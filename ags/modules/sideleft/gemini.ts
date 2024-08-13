import Gtk from "gi://Gtk?version=3.0";
import GeminiService from "services/gemini.ts";
import { MaterialIcon } from "icons.ts";
import { ChatMessage, SystemMessage } from "modules/misc/chat_message.ts";
import { markdownTest } from "modules/misc/md2pango.ts";
import Gdk from "gi://Gdk";
import { enable_click_through } from "../misc/clickthrough.js";
import { TextView } from "modules/misc/textview.js";

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
    attribute: { placeholder: "Message Gemini..." },
    setup: (self: any) => {
        self.set_valign(Gtk.Align.CENTER);
        self.hook(
            GeminiService,
            () => {
                self.attribute.placeholder =
                    GeminiService.key.length > 0 ? "Message Gemini..." : "Enter Google AI API Key...";
                chatPlaceholder.label = self.attribute.placeholder;
            },
            "hasKey"
        ).on("key-press-event", (widget, event) => {
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

const GeminiInfo = () => {
    const geminiLogo = Widget.Icon({
        hpack: "center",
        class_name: "info",
        icon: `google-gemini-symbolic`
    });
    return Widget.Box({
        vertical: true,
        spacing: 15,
        children: [
            geminiLogo,
            Widget.Label({
                class_name: "name",
                wrap: true,
                justify: Gtk.Justification.CENTER,
                label: "Assistant (Gemini)"
            }),
            Widget.Box({
                spacing: 5,
                hpack: "center",
                children: [
                    Widget.Label({
                        class_name: "description",
                        wrap: true,
                        justify: Gtk.Justification.CENTER,
                        label: "Powered by Google"
                    }),
                    Widget.Button({
                        class_name: "description icon material_icon",
                        label: "info",
                        tooltipText:
                            "Uses gemini-pro.\nNot affiliated, endorsed, or sponsored by Google.\n\nPrivacy: Chat messages aren't linked to your account,\n    but will be read by human reviewers to improve the model."
                    })
                ]
            })
        ]
    });
};

const GoogleAiInstructions = () =>
    Widget.Box({
        homogeneous: true,
        children: [
            Widget.Revealer({
                transition: "slide_down",
                transitionDuration: 200,
                setup: (self) =>
                    self.hook(
                        GeminiService,
                        (self, hasKey) => {
                            self.reveal_child = GeminiService.key.length == 0;
                        },
                        "hasKey"
                    ),
                child: Widget.Button({
                    child: Widget.Label({
                        useMarkup: true,
                        wrap: true,
                        class_name: "instructions",
                        justify: Gtk.Justification.CENTER,
                        label: "A Google AI API key is required\nYou can grab one <u>here</u>, then enter it below"
                        // setup: self => self.set_markup("This is a <a href=\"https://www.github.com\">test link</a>")
                    }),
                    onClicked: () => {
                        Utils.execAsync(["bash", "-c", `xdg-open https://makersuite.google.com/app/apikey &`]);
                    }
                })
            })
        ]
    });

const geminiWelcome = Widget.Box({
    vexpand: true,
    homogeneous: true,
    child: Widget.Box({
        vpack: "center",
        spacing: 15,
        vertical: true,
        children: [GeminiInfo(), GoogleAiInstructions()]
    })
});

const chatContent = Widget.Box({
    vertical: true,
    spacing: 5,
    setup: (self) =>
        self.hook(
            GeminiService,
            (box, id) => {
                const message = GeminiService.messages[id];
                if (!message) return;
                box.add(ChatMessage(message, "Gemini"));
            },
            "newMsg"
        )
});

const clearChat = () => {
    GeminiService.clear();
    const children = chatContent.get_children();
    for (let i = 0; i < children.length; i++) {
        const child = children[i];
        child.destroy();
    }
};

const CommandButton = (command) =>
    Widget.Button({
        class_name: "command_button filled_tonal_button",
        onClicked: () => sendMessage(command),
        label: command
    });

const geminiCommands = Widget.Box({
    spacing: 5,
    class_name: "command_buttons",
    children: [Widget.Box({ hexpand: true }), CommandButton("/key"), CommandButton("/model"), CommandButton("/clear")]
});

const sendMessage = (text) => {
    // Check if text or API key is empty
    if (text.length == 0) return;
    if (GeminiService.key.length == 0) {
        GeminiService.key = text;
        chatContent.add(SystemMessage(`Key saved to\n\`${GeminiService.keyPath}\``, "API Key", geminiView));
        text = "";
        return;
    }
    // Commands
    if (text.startsWith("/")) {
        if (text.startsWith("/clear")) clearChat();
        else if (text.startsWith("/load")) {
            clearChat();
            GeminiService.loadHistory();
        } else if (text.startsWith("/model"))
            chatContent.add(SystemMessage(`Currently using \`${GeminiService.modelName}\``, "/model", geminiView));
        else if (text.startsWith("/prompt")) {
            const firstSpaceIndex = text.indexOf(" ");
            const prompt = text.slice(firstSpaceIndex + 1);
            if (firstSpaceIndex == -1 || prompt.length < 1) {
                chatContent.add(SystemMessage(`Usage: \`/prompt MESSAGE\``, "/prompt", geminiView));
            } else {
                GeminiService.addMessage("user", prompt);
            }
        } else if (text.startsWith("/key")) {
            const parts = text.split(" ");
            if (parts.length == 1)
                chatContent.add(
                    SystemMessage(
                        `Key stored in:\n\`${GeminiService.keyPath}\`\nTo update this key, type \`/key YOUR_API_KEY\``,
                        "/key",
                        geminiView
                    )
                );
            else {
                GeminiService.key = parts[1];
                chatContent.add(SystemMessage(`Updated API Key at\n\`${GeminiService.keyPath}\``, "/key", geminiView));
            }
        } else if (text.startsWith("/test")) chatContent.add(SystemMessage(markdownTest, `Markdown test`, geminiView));
        else chatContent.add(SystemMessage(`Invalid command.`, "Error", geminiView));
    } else {
        GeminiService.send(text);
    }
};

const geminiView = Widget.Box({
    homogeneous: true,
    children: [
        Widget.Scrollable({
            vexpand: true,
            hscroll: "never",
            child: Widget.Box({
                vertical: true,
                children: [geminiWelcome, chatContent]
            }),
            setup: (scrolledWindow) => {
                // Show scrollbar
                scrolledWindow.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC);
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

export const geminiPage = Widget.Box({
    class_name: "page gemini",
    vertical: true,
    children: [geminiView, geminiCommands, textboxArea]
});
