import Gtk from "gi://Gtk?version=3.0";
import { MaterialIcon } from "icons.ts";
import Gdk from "gi://Gdk";
import { enable_click_through } from "../misc/clickthrough.js";
import type * as Types from "services/chatroom.d.ts";
import { chatrooms } from "services/chatrooms.ts";
import { MessageContent } from "modules/misc/chat_message.ts";
import { TextView } from "modules/misc/textview.js";

const ChatMessage = (message: Types.ChatMessage) => {
    const messageContentBox = MessageContent(message.message);
    const thisMessage = Widget.Box({
        class_name: "message",
        attribute: { id: message.id },
        children: [
            // @ts-expect-error
            Widget.Box({
                vertical: true,
                children: [
                    message.type == 3 || (message.type == 4 && message.nickname == "system")
                        ? undefined
                        : Widget.Label({
                              hpack: "start",
                              xalign: 0,
                              class_name: `chat_name`,
                              wrap: true,
                              use_markup: false,
                              label: message.nickname
                          }),
                    Widget.Box({
                        homogeneous: true,
                        class_name: "chat_message_box",
                        children: [messageContentBox]
                    })
                ]
            })
        ],
        setup: (self) => {
            if (message.type == 4) {
                self.toggleClassName("ephemeral", true);
            }
        }
    });
    return thisMessage;
};

function apiSendMessage(textView: any) {
    // Get text
    const buffer = textView.get_buffer();
    const [start, end] = buffer.get_bounds();
    const text = buffer.get_text(start, end, true).trimStart();
    if (!text || text.length == 0) return;
    // Send
    sendMessage(text);
    // Reset
    buffer.set_text("", -1);
    chatEntryWrapper.toggleClassName("chat_wrapper_extended", false);
    chatEntry.set_valign(Gtk.Align.CENTER);
}

const chatEntry: any = TextView({
    hexpand: true,
    wrap_mode: Gtk.WrapMode.WORD_CHAR,
    accepts_tab: false,
    class_name: "chat_entry",
    attribute: { placeholder: "Send message..." },
    setup: (self: any) => {
        self.set_valign(Gtk.Align.CENTER);
        self.on("key-press-event", (widget, event) => {
            // Don't send when Shift+Enter
            if (event.get_keyval()[1] === Gdk.KEY_Return) {
                if (event.get_state()[1] !== 17) {
                    // SHIFT_MASK doesn't work but 17 should be shift
                    apiSendMessage(widget);
                    return true;
                }
                return false;
            }
        });
    }
});

const chatEntryWrapper = Widget.Scrollable({
    class_name: "chat_wrapper",
    hscroll: "never",
    vscroll: "always",
    child: chatEntry,
    setup: (self) => {
        chatEntry.connect("focus-in-event", () => {
            textboxArea.toggleClassName("focused", true);
        });
        chatEntry.connect("focus-out-event", () => {
            textboxArea.toggleClassName("focused", false);
        });
    }
});

chatEntry.get_buffer().connect("changed", (buffer) => {
    const bufferText = buffer.get_text(buffer.get_start_iter(), buffer.get_end_iter(), true);
    // chatSendButton.toggleClassName("chat_wrapper_extended", bufferText.length > 0);
    chatPlaceholderRevealer.reveal_child = bufferText.length == 0;
    if (buffer.get_line_count() > 2 || bufferText.length > 30) {
        chatEntryWrapper.toggleClassName("chat_wrapper_extended", true);
        chatEntry.set_valign(Gtk.Align.FILL);
        chatPlaceholder.set_valign(Gtk.Align.FILL);
    } else {
        chatEntryWrapper.toggleClassName("chat_wrapper_extended", false);
        chatEntry.set_valign(Gtk.Align.CENTER);
        chatPlaceholder.set_valign(Gtk.Align.CENTER);
    }
});

const chatPlaceholder = Widget.Label({
    className: "placeholder",
    hpack: "start",
    vpack: "center",
    label: chatEntry.attribute.placeholder
});

const chatPlaceholderRevealer = Widget.Revealer({
    revealChild: true,
    transition: "crossfade",
    transitionDuration: 200,
    child: chatPlaceholder,
    setup: enable_click_through
});

const chatSendButton = Widget.Button({
    className: "send standard_icon_button",
    child: MaterialIcon("send", "24px"),
    vpack: "center",
    hpack: "end",
    css: "font-size: 24px",
    onClicked: (self) => {
        apiSendMessage(chatEntry);
    }
});

const textboxArea = Widget.Box({
    // Entry area
    className: "textbox",
    children: [
        Widget.Overlay({
            passThrough: true,
            child: chatEntryWrapper,
            overlays: [chatPlaceholderRevealer]
        }),
        Widget.Box({ className: "width-10" }),
        chatSendButton
    ]
});

const chatContent = Widget.Box({
    vertical: true,
    spacing: 2,
    vpack: "end",
    setup: (self) =>
        chatrooms.connect("new-messages", (_, messages: Types.ChatMessage[]) => {
            let i = 0;
            for (const message of messages) {
                i++;
                Utils.timeout(i * 10, () => {
                    if (message.type == 4) {
                        self.pack_start(ChatMessage(message), false, false, 0);
                    } else {
                        // @ts-ignore
                        const _ = self.children.find((n) => n.attribute.id === message.id);
                        if (!_) self.pack_start(ChatMessage(message), false, false, 0);
                    }
                });
            }
        })
});

const sendMessage = (text: string) => {
    if (text.trim().toLowerCase() == "/exit") {
        current.setValue("room");
        chatrooms.login_success = false;
    } else chatrooms.send_message(text);
};

const View = Widget.Box({
    homogeneous: true,
    children: [
        Widget.Scrollable({
            vexpand: true,
            hscroll: "never",
            child: Widget.Box({
                vertical: true,
                vpack: "end",
                children: [chatContent]
            }),
            setup: (scrolledWindow) => {
                // Show scrollbar
                scrolledWindow.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.ALWAYS);
                const vScrollbar = scrolledWindow.get_vscrollbar();
                vScrollbar.get_style_context().add_class("sidebar-scrollbar");
                // Avoid click-to-scroll-widget-to-view behavior
                Utils.timeout(1, () => {
                    const viewport = scrolledWindow.child;
                    viewport.set_focus_vadjustment(new Gtk.Adjustment(undefined));
                });
                // Always scroll to bottom with new content
                const adjustment = scrolledWindow.get_vadjustment();
                adjustment.connect("changed", () =>
                    Utils.timeout(1, () => {
                        if (!chatEntry.hasFocus) return;
                        adjustment.set_value(adjustment.get_upper() - adjustment.get_page_size());
                    })
                );
            }
        })
    ]
});

const current = Variable("server_ip");

const _chat_page = Widget.Box({
    vertical: true,
    children: [View, textboxArea]
});

let room_key = "";

const _room_key = Widget.Box({
    vertical: true,
    class_name: "room",
    spacing: 5,
    children: [
        Widget.Entry({
            vpack: "center",
            hexpand: true,
            placeholder_text: "Room key",
            on_change: (self) => {
                room_key = self.text || "";
            }
        }),
        Widget.Box({
            hexpand: true,
            spacing: 5,
            children: [
                Widget.Box({
                    hexpand: true,
                    child: Widget.Button({
                        vpack: "center",
                        hpack: "start",
                        label: "Create new room",
                        class_name: "filled_tonal_button",
                        on_clicked: (self) => {
                            chatrooms.create_room().then((r) => {
                                if (r.data.success) {
                                    Utils.execAsync(`wl-copy ${r.data.key}`);
                                    Utils.execAsync(
                                        `notify-send -u critical "Chatrooms" "You have just created a chatroom and the key has been copied to your clipboard"`
                                    );
                                }
                            });
                        }
                    })
                }),
                Widget.Button({
                    vpack: "center",
                    hpack: "end",
                    label: "Join",
                    class_name: "filled_button",
                    on_clicked: (self) => {
                        chatrooms.set_room(room_key).then((r) => {
                            if (r.data.success) current.setValue("login");
                        });
                    }
                })
            ]
        })
    ]
});

let username = "";
let password = "";

const _login = Widget.Box({
    vertical: true,
    spacing: 5,
    vpack: "start",
    class_name: "login",
    children: [
        Widget.Entry({
            placeholder_text: "Username",
            hexpand: true,
            text: chatrooms.bind("username"),
            on_change: (self) => {
                username = self.text || "";
            }
        }),
        Widget.Entry({
            placeholder_text: "Password",
            hexpand: true,
            visibility: false,
            on_change: (self) => {
                password = self.text || "";
            }
        }),
        Widget.Box({
            hexpand: true,
            children: [
                Widget.Box({
                    hexpand: true,
                    child: Widget.Button({
                        vpack: "center",
                        hpack: "start",
                        label: "Exit",
                        class_name: "filled_tonal_button",
                        on_clicked: (self) => {
                            current.setValue("room");
                        }
                    })
                }),
                Widget.Box({
                    hpack: "end",
                    spacing: 5,
                    children: [
                        Widget.Button({
                            vpack: "center",
                            hpack: "end",
                            label: "Register",
                            class_name: "filled_tonal_button",
                            on_clicked: (self) => {
                                chatrooms.create_user(username, password).then((r) => {
                                    if (r.data.success && !r.data.wait_for_accept) current.setValue("chat");
                                });
                            }
                        }),
                        Widget.Button({
                            vpack: "center",
                            hpack: "end",
                            label: "Login",
                            class_name: "filled_button",
                            on_clicked: (self) => {
                                chatrooms.login(username, password).then((r) => {
                                    if (r.data.success) current.setValue("chat");
                                });
                            }
                        })
                    ]
                })
            ]
        })
    ]
});

let server_ip = "";

const _server_ip = Widget.Box({
    vertical: true,
    class_name: "room",
    spacing: 5,
    children: [
        Widget.Entry({
            vpack: "center",
            hexpand: true,
            placeholder_text: "Server ip",
            on_change: (self) => {
                server_ip = self.text || "";
            }
        }),
        Widget.Box({
            hexpand: true,
            spacing: 5,
            children: [
                Widget.Button({
                    vpack: "center",
                    hpack: "end",
                    label: "Use",
                    class_name: "filled_button",
                    on_clicked: (self) => {
                        chatrooms.ip = server_ip;
                    }
                })
            ]
        }),
        Widget.Box({
            vertical: true,
            children: [
                Widget.Box({
                    spacing: 5,
                    children: [
                        MaterialIcon("info", "20px"),
                        Widget.Label({
                            label: "Chatrooms is still in beta.",
                            vpack: "center",
                            hpack: "center"
                        })
                    ]
                }),
                Widget.Box({
                    spacing: 5,
                    children: [
                        MaterialIcon("info", "20px"),
                        Widget.Box({
                            hexpand: true,
                            child: Widget.Label({
                                label: "You can find the source for the API at \nhttps://github.com/koeqaife/chatrooms-api",
                                selectable: true,
                                vpack: "center",
                                hpack: "start"
                            })
                        })
                    ]
                })
            ]
        })
    ]
});

chatrooms.connect("room-changed", () => {
    current.setValue("login");
    chatContent.children = [];
});

chatrooms.connect("ip-changed", () => {
    current.setValue("room");
});

let last_error = "";

chatrooms.connect("changed", () => {
    if (last_error != chatrooms.last_error) {
        // prettier-ignore
        Utils.execAsync([
            "notify-send",
            "-u", "critical",
            "Chatrooms",
            chatrooms.last_error
        ]);
        last_error = chatrooms.last_error;
    }
});

export const chatsPage = Widget.Stack({
    class_name: "page chats",
    children: {
        room: _room_key,
        chat: _chat_page,
        login: _login,
        server_ip: _server_ip
    },
    // @ts-expect-error
    shown: current.bind(),
    transition: "crossfade",
    transition_duration: 200
});
