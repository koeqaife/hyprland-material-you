from __future__ import annotations
import os
import typing as t
import asyncio
import struct

from repository import gio, glib
from utils.logger import logger
from utils.service import Service
from config import Settings
from src.services.state import is_locked
from src.services.login1 import get_login_manager
from src.services.mpris import players
from src.services import hyprland


def handle_lid_action() -> None:
    """Handle laptop lid close action based on user settings"""
    logger.debug("handle_lid_action called")
    
    if not os.path.exists("/proc/acpi/button/lid"):
        logger.debug("Lid device not found")
        return
        
    action = Settings().get("lid_action")
    if not action:
        action = "nothing"
    
    logger.debug(f"Lid action: {action}")
    
    if action == "lock":
        logger.debug("Locking screen")
        is_locked.value = True
    elif action == "sleep":
        logger.debug("Going to sleep")
        is_locked.value = True
        for player in players.value.values():
            player.pause()
        get_login_manager().suspend()
    elif action == "dpms":
        logger.debug("Turning off displays")
        asyncio.create_task(
            hyprland.client.raw("dispatch dpms off")
        )
    else:
        logger.debug("No action taken")


class LidMonitor(Service):
    """Monitor laptop lid state using input events"""
    
    def __init__(self) -> None:
        super().__init__()
        self.lid_device_path: str | None = None
        self.fd: int | None = None
        self.watch_id: int | None = None
        
    def _find_lid_device(self) -> str | None:
        """Find the input device for lid switch"""
        try:
            with open('/proc/bus/input/devices', 'r') as f:
                content = f.read()
            
            # Split into device blocks
            devices = content.split('\n\n')
            
            for device in devices:
                if 'Lid Switch' in device:
                    for line in device.split('\n'):
                        if line.startswith('H: Handlers='):
                            handlers = line.split('=')[1].strip()
                            for handler in handlers.split():
                                if handler.startswith('event'):
                                    event_path = f"/dev/input/{handler}"
                                    if os.path.exists(event_path):
                                        logger.debug(f"Found lid device: {event_path}")
                                        return event_path
            
            logger.warning("Lid Switch device not found in /proc/bus/input/devices")
            return None
            
        except Exception as e:
            logger.error(f"Failed to find lid device: {e}")
            return None
        
    def app_init(self) -> None:
        """Initialize the lid monitor service"""
        if os.path.exists("/proc/acpi/button/lid"):
            self.lid_device_path = self._find_lid_device()
            if self.lid_device_path:
                self.start_monitoring()
            else:
                logger.warning("Lid device not found, lid monitoring disabled")
    
    def start_monitoring(self) -> None:
        """Start monitoring lid state using input events"""
        if self.fd is not None or not self.lid_device_path:
            return
            
        try:
            if not os.path.exists(self.lid_device_path):
                logger.error(f"Lid device {self.lid_device_path} not found")
                return
                
            self.fd = os.open(self.lid_device_path, os.O_RDONLY | os.O_NONBLOCK)
            self.watch_id = glib.io_add_watch(
                self.fd, 
                glib.IO_IN, 
                self._on_input_event
            )
            
            logger.debug(f"Started lid monitoring on {self.lid_device_path}")
            
        except Exception as e:
            logger.error(f"Failed to start lid monitoring: {e}")
    
    def on_close(self) -> None:
        """Stop monitoring lid state"""
        if self.watch_id is not None:
            glib.source_remove(self.watch_id)
            self.watch_id = None
        if self.fd is not None:
            os.close(self.fd)
            self.fd = None
        logger.debug("Stopped lid monitoring")
    
    def _on_input_event(self, fd: int, condition: glib.IOCondition) -> bool:
        """Handle input events from lid switch"""
        try:
            # Read input event (struct input_event is 24 bytes on 64-bit)
            data = os.read(fd, 24)
            if len(data) < 24:
                return True
                
            # Unpack input_event structure: sec, usec, type, code, value
            sec, usec, event_type, code, value = struct.unpack('llHHi', data)
            
            logger.debug(f"Input event - type: {event_type}, code: {code}, value: {value}")
            
            # SW_LID is code 0, type 5 (EV_SW)
            if event_type == 5 and code == 0:  # EV_SW and SW_LID
                if value == 1:  # Lid closed
                    logger.debug("Lid closed, triggering action")
                    self._trigger_lid_action()
                elif value == 0:  # Lid opened
                    logger.debug("Lid opened")
                    
        except Exception as e:
            logger.error(f"Error reading input event: {e}")
            
        return True  # Keep watching
    
    def _trigger_lid_action(self) -> None:
        """Trigger lid action in main thread"""
        try:
            handle_lid_action()
        except Exception as e:
            logger.error(f"Failed to handle lid action: {e}")


# Create service instance
LidService = LidMonitor
