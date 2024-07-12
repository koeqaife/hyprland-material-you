const { Gdk, Gio, GLib, Gtk } = imports.gi;
// @ts-expect-error
import GtkSource from "gi://GtkSource?version=3.0";
const { Box, Button, Label, Icon, Scrollable, Stack } = Widget;
const { execAsync, exec } = Utils;
import { MaterialIcon } from "icons.ts";
import md2pango from "./md2pango.ts";
import { theme } from "variables.ts";
import Pango10 from "gi://Pango?version=1.0";

const LATEX_DIR = `${GLib.get_user_cache_dir()}/ags/media/latex`;
const USERNAME = GLib.get_user_name();

function substituteLang(str) {
    const subs = [
        { from: "javascript", to: "js" },
        { from: "bash", to: "sh" }
    ];
    for (const { from, to } of subs) {
        if (from === str) return to;
    }
    return str;
}

const HighlightedCode = (content, lang) => {
    const buffer = new GtkSource.Buffer();
    const sourceView = new GtkSource.View({
        buffer: buffer,
        wrap_mode: Gtk.WrapMode.NONE
    });
    const langManager = GtkSource.LanguageManager.get_default();
    let displayLang = langManager.get_language(substituteLang(lang));
    if (displayLang) {
        buffer.set_language(displayLang);
    }
    const CUSTOM_SCHEME_ID = `custom${theme.value == "dark" ? "" : "-light"}`;
    const schemeManager = GtkSource.StyleSchemeManager.get_default();
    buffer.set_style_scheme(schemeManager.get_scheme(CUSTOM_SCHEME_ID));
    buffer.set_text(content, -1);
    return sourceView;
};

const TextBlock = (content = "") =>
    Label({
        hpack: "fill",
        class_name: "text_block",
        useMarkup: true,
        xalign: 0,
        wrap: true,
        wrap_mode: Pango10.WrapMode.WORD_CHAR,
        selectable: true,
        label: content
    });

Utils.execAsync(["bash", "-c", `rm -rf ${LATEX_DIR}`])
    .then(() => Utils.execAsync(["bash", "-c", `mkdir -p ${LATEX_DIR}`]))
    .catch(print);

const Latex = (content = "") => {
    const latexViewArea = Box({
        // vscroll: 'never',
        // hscroll: 'automatic',
        // homogeneous: true,
        attribute: {
            render: async (self, text) => {
                if (text.length == 0) return;
                const styleContext = self.get_style_context();
                const fontSize = styleContext.get_property("font-size", Gtk.StateFlags.NORMAL);

                const timeSinceEpoch = Date.now();
                const fileName = `${timeSinceEpoch}.tex`;
                const outFileName = `${timeSinceEpoch}-symbolic.svg`;
                const outIconName = `${timeSinceEpoch}-symbolic`;
                const scriptFileName = `${timeSinceEpoch}-render.sh`;
                const filePath = `${LATEX_DIR}/${fileName}`;
                const outFilePath = `${LATEX_DIR}/${outFileName}`;
                const scriptFilePath = `${LATEX_DIR}/${scriptFileName}`;

                Utils.writeFile(text, filePath).catch(print);
                // Since MicroTex doesn't support file path input properly, we gotta cat it
                // And escaping such a command is a fucking pain so I decided to just generate a script
                // Note: MicroTex doesn't support `&=`
                // You can add this line in the middle for debugging: echo "$text" > ${filePath}.tmp
                const renderScript = `#!/usr/bin/env bash
text=$(cat ${filePath} | sed 's/$/ \\\\\\\\/g' | sed 's/&=/=/g')
cd /opt/MicroTeX
./LaTeX -headless -input="$text" -output=${outFilePath} -textsize=${fontSize * 1.1} -padding=0 -maxwidth=${
                    latexViewArea.get_allocated_width() * 0.85
                } > /dev/null 2>&1
sed -i 's/fill="rgb(0%, 0%, 0%)"/style="fill:#000000"/g' ${outFilePath}
sed -i 's/stroke="rgb(0%, 0%, 0%)"/stroke="${theme.value == "dark" ? "#ffffff" : "#000000"}"/g' ${outFilePath}
`;
                Utils.writeFile(renderScript, scriptFilePath).catch(print);
                Utils.exec(`chmod a+x ${scriptFilePath}`);
                Utils.timeout(100, () => {
                    Utils.exec(`bash ${scriptFilePath}`);
                    Gtk.IconTheme.get_default().append_search_path(LATEX_DIR);

                    self.child?.destroy();
                    self.child = Gtk.Image.new_from_icon_name(outIconName, 0);
                });
            }
        },
        setup: (self) => self.attribute.render(self, content).catch(print)
    });
    const wholeThing = Box({
        class_name: "latex",
        homogeneous: true,
        attribute: {
            updateText: (text) => {
                latexViewArea.attribute.render(latexViewArea, text).catch(print);
            }
        },
        children: [
            Scrollable({
                vscroll: "never",
                hscroll: "automatic",
                child: latexViewArea
            })
        ]
    });
    return wholeThing;
};

const CodeBlock = (content = "", lang = "txt") => {
    if (lang == "tex" || lang == "latex") {
        return Latex(content);
    }
    const topBar = Box({
        class_name: "codeblock_top_bar",
        children: [
            Label({
                label: lang,
                class_name: "codeblock_top_bar_text"
            }),
            Box({
                hexpand: true
            }),
            Button({
                class_name: "codeblock_top_bar_button standard_button",
                child: Box({
                    spacing: 5,
                    children: [
                        MaterialIcon("content_copy", "small"),
                        Label({
                            label: "Copy"
                        })
                    ]
                }),
                onClicked: (self) => {
                    const buffer = sourceView.get_buffer();
                    const copyContent = buffer.get_text(buffer.get_start_iter(), buffer.get_end_iter(), false); // TODO: fix this
                    execAsync([`wl-copy`, `${copyContent}`]).catch(print);
                }
            })
        ]
    });
    // Source view
    const sourceView = HighlightedCode(content, lang);

    const codeBlock = Box({
        attribute: {
            updateText: (text) => {
                sourceView.get_buffer().set_text(text, -1);
            }
        },
        class_name: "codeblock",
        vertical: true,
        children: [
            topBar,
            Box({
                class_name: "codeblock_code",
                homogeneous: true,
                children: [
                    Scrollable({
                        vscroll: "never",
                        hscroll: "automatic",
                        child: sourceView
                    })
                ]
            })
        ]
    });

    // const schemeIds = styleManager.get_scheme_ids();

    // print("Available Style Schemes:");
    // for (let i = 0; i < schemeIds.length; i++) {
    //     print(schemeIds[i]);
    // }
    return codeBlock;
};

const Divider = () =>
    Box({
        class_name: "divider"
    });

export const MessageContent = (content) => {
    const contentBox = Box({
        vertical: true,
        attribute: {
            fullUpdate: (self, content: string, useCursor = false) => {
                // Clear and add first text widget
                const children = contentBox.get_children();
                for (let i = 0; i < children.length; i++) {
                    const child = children[i];
                    child.destroy();
                }
                contentBox.add(TextBlock());
                // Loop lines. Put normal text in markdown parser
                // and put code into code highlighter (TODO)
                let lines = content.split("\n");
                let lastProcessed = 0;
                let inCode = false;
                for (const [index, line] of lines.entries()) {
                    // Code blocks
                    const codeBlockRegex = /^\s*```([a-zA-Z0-9]+)?\n?/;
                    if (codeBlockRegex.test(line)) {
                        const kids = self.get_children();
                        const lastLabel = kids[kids.length - 1];
                        const blockContent = lines.slice(lastProcessed, index).join("\n");
                        if (!inCode) {
                            lastLabel.label = md2pango(blockContent);
                            contentBox.add(CodeBlock("", (codeBlockRegex.exec(line) || [])[1]));
                        } else {
                            lastLabel.attribute.updateText(blockContent);
                            contentBox.add(TextBlock());
                        }

                        lastProcessed = index + 1;
                        inCode = !inCode;
                    }
                    // Breaks
                    const dividerRegex = /^\s*---/;
                    if (!inCode && dividerRegex.test(line)) {
                        const kids = self.get_children();
                        const lastLabel = kids[kids.length - 1];
                        const blockContent = lines.slice(lastProcessed, index).join("\n");
                        lastLabel.label = md2pango(blockContent);
                        contentBox.add(Divider());
                        contentBox.add(TextBlock());
                        lastProcessed = index + 1;
                    }
                }
                if (lastProcessed < lines.length) {
                    const kids = self.get_children();
                    const lastLabel = kids[kids.length - 1];
                    let blockContent = lines.slice(lastProcessed, lines.length).join("\n");
                    if (!inCode) lastLabel.label = `${md2pango(blockContent)}${useCursor ? " ..." : ""}`;
                    else lastLabel.attribute.updateText(blockContent);
                }
                // Debug: plain text
                // contentBox.add(Label({
                //     hpack: 'fill',
                //     class_name: 'txt sidebar-chat-txtblock sidebar-chat-txt',
                //     useMarkup: false,
                //     xalign: 0,
                //     wrap: true,
                //     selectable: true,
                //     label: '------------------------------\n' + md2pango(content),
                // }))
                contentBox.show_all();
            }
        }
    });
    contentBox.attribute.fullUpdate(contentBox, content, false);
    return contentBox;
};

export const ChatMessage = (message, modelName = "Model") => {
    const TextSkeleton = (extraClassName = "") =>
        Box({
            class_name: `skeleton_line ${extraClassName}`,
            hpack: "start",
            vpack: "center"
        });
    const messageContentBox = MessageContent(message.content);
    const messageLoadingSkeleton = Box({
        vertical: false,
        spacing: 5,
        children: Array.from({ length: 3 }, (_, id) => TextSkeleton(`skeleton_line_offset${id}`))
    });
    const messageArea = Stack({
        homogeneous: message.role !== "user",
        transition: "crossfade",
        transitionDuration: 200,
        children: {
            thinking: messageLoadingSkeleton,
            message: messageContentBox
        },
        shown: message.thinking ? "thinking" : "message"
    });
    const thisMessage = Box({
        class_name: "message",
        homogeneous: true,
        children: [
            Box({
                vertical: true,
                children: [
                    Label({
                        hpack: "start",
                        xalign: 0,
                        class_name: `chat_name chat_name_${message.role == "user" ? "user" : "bot"}`,
                        wrap: true,
                        useMarkup: true,
                        label: message.role == "user" ? USERNAME : modelName
                    }),
                    Box({
                        homogeneous: true,
                        class_name: "chat_message_box",
                        children: [messageArea]
                    })
                ],
                setup: (self) =>
                    self
                        .hook(
                            message,
                            (self, isThinking) => {
                                messageArea.shown = message.thinking ? "thinking" : "message";
                            },
                            "notify::thinking"
                        )
                        .hook(
                            message,
                            (self) => {
                                // Message update
                                messageContentBox.attribute.fullUpdate(
                                    messageContentBox,
                                    message.content,
                                    message.role != "user"
                                );
                            },
                            "notify::content"
                        )
                        .hook(
                            message,
                            (label, isDone) => {
                                // Remove the cursor
                                messageContentBox.attribute.fullUpdate(messageContentBox, message.content, false);
                            },
                            "notify::done"
                        )
            })
        ]
    });
    return thisMessage;
};

export const SystemMessage = (content, commandName, scrolledWindow) => {
    const messageContentBox = MessageContent(content);
    const thisMessage = Box({
        class_name: "message",
        children: [
            Box({
                vertical: true,
                children: [
                    Label({
                        xalign: 0,
                        hpack: "start",
                        class_name: "chat_name chat_name_system",
                        wrap: true,
                        label: `System  •  ${commandName}`
                    }),
                    messageContentBox
                ]
            })
        ]
    });
    return thisMessage;
};
