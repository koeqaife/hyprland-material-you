#!/usr/bin/env node
import { readFile, writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const rootDir = path.resolve(__dirname, "..");
const colorsFile = path.join(rootDir, "themes", "colors.json");
const outputFile = path.join(rootDir, "themes", "m3e-color-theme.json");

function pick(palette, key, fallback) {
  return palette?.[key] ?? fallback;
}

function buildTheme(palette) {
  const background = pick(palette, "background", "#1c110d");
  const foreground = pick(palette, "onBackground", "#f5ded8");
  const surface = pick(palette, "surface", background);
  const surfaceHigh = pick(palette, "surfaceContainerHigh", "#342723");
  const surfaceHighest = pick(palette, "surfaceContainerHighest", "#40322e");
  const surfaceVariant = pick(palette, "surfaceVariant", "#58423b");
  const outline = pick(palette, "outline", "#a78a83");
  const onSurfaceVariant = pick(palette, "onSurfaceVariant", foreground);
  const primary = pick(palette, "primary", "#a5c8ff");
  const secondary = pick(palette, "secondary", "#edbe91");
  const tertiary = pick(palette, "tertiary", "#add198");
  const tertiaryDim = pick(palette, "tertiaryDim", "#d6fcc0");
  const error = pick(palette, "error", "#ffb4ab");

  return {
    $schema: "vscode://schemas/color-theme",
    name: "Material 3 Expressive Red",
    type: "dark",
    semanticHighlighting: true,
    colors: {
      "editor.background": background,
      "editor.foreground": foreground,
      "editorCursor.foreground": primary,
      "editor.selectionBackground": surfaceHighest,
      "editor.inactiveSelectionBackground": surfaceHigh,
      "editor.lineHighlightBackground": surfaceHigh,
      "editorLineNumber.foreground": outline,
      "editorLineNumber.activeForeground": foreground,
      "editorIndentGuide.background1": surfaceVariant,
      "editorIndentGuide.activeBackground1": onSurfaceVariant,
      "editorWhitespace.foreground": surfaceVariant,
      "editorWidget.background": surface,
      "editorWidget.border": surfaceVariant,
      "editorHoverWidget.background": surface,
      "editorHoverWidget.border": surfaceVariant,
      "editorSuggestWidget.background": surface,
      "editorSuggestWidget.border": surfaceVariant,
      "editorSuggestWidget.selectedBackground": surfaceHigh,
      "activityBar.background": surface,
      "activityBar.foreground": foreground,
      "activityBar.inactiveForeground": outline,
      "activityBarBadge.background": primary,
      "activityBarBadge.foreground": pick(palette, "onPrimary", "#00315f"),
      "sideBar.background": pick(palette, "surfaceContainerLow", "#251915"),
      "sideBar.foreground": foreground,
      "sideBar.border": surfaceVariant,
      "titleBar.activeBackground": surface,
      "titleBar.activeForeground": foreground,
      "titleBar.inactiveBackground": pick(palette, "surfaceContainerLow", surface),
      "titleBar.inactiveForeground": outline,
      "statusBar.background": pick(palette, "surfaceContainer", "#291d19"),
      "statusBar.foreground": foreground,
      "statusBar.debuggingBackground": secondary,
      "statusBar.debuggingForeground": pick(palette, "onSecondary", "#462a09"),
      "tab.activeBackground": surface,
      "tab.activeForeground": foreground,
      "tab.inactiveBackground": pick(palette, "surfaceContainerLow", "#251915"),
      "tab.inactiveForeground": outline,
      "tab.border": surfaceVariant,
      "panel.background": pick(palette, "surfaceContainer", "#291d19"),
      "panel.border": surfaceVariant,
      "panelTitle.activeForeground": foreground,
      "panelTitle.inactiveForeground": outline,
      "input.background": surfaceHigh,
      "input.foreground": foreground,
      "input.border": surfaceVariant,
      "input.placeholderForeground": outline,
      "button.background": primary,
      "button.foreground": pick(palette, "onPrimary", "#00315f"),
      "button.hoverBackground": pick(palette, "primaryDim", primary),
      "dropdown.background": surfaceHigh,
      "dropdown.foreground": foreground,
      "dropdown.border": surfaceVariant,
      "list.activeSelectionBackground": surfaceHighest,
      "list.activeSelectionForeground": foreground,
      "list.inactiveSelectionBackground": surfaceHigh,
      "list.inactiveSelectionForeground": foreground,
      "list.hoverBackground": surfaceHigh,
      "list.focusBackground": surfaceHighest,
      "list.focusForeground": foreground,
      "list.highlightForeground": primary,
      "peekView.border": surfaceVariant,
      "peekViewEditor.background": surface,
      "peekViewResult.background": pick(palette, "surfaceContainer", "#291d19"),
      "peekViewTitle.background": surfaceHigh,
      "badge.background": primary,
      "badge.foreground": pick(palette, "onPrimary", "#00315f"),
      "terminal.background": background,
      "terminal.foreground": foreground,
      "terminal.ansiBlack": background,
      "terminal.ansiRed": error,
      "terminal.ansiGreen": tertiary,
      "terminal.ansiYellow": secondary,
      "terminal.ansiBlue": primary,
      "terminal.ansiMagenta": pick(palette, "primaryContainer", "#17477d"),
      "terminal.ansiCyan": tertiaryDim,
      "terminal.ansiWhite": foreground,
      "terminal.ansiBrightBlack": outline,
      "terminal.ansiBrightRed": pick(palette, "errorDim", error),
      "terminal.ansiBrightGreen": tertiaryDim,
      "terminal.ansiBrightYellow": pick(palette, "secondaryDim", secondary),
      "terminal.ansiBrightBlue": pick(palette, "primaryDim", primary),
      "terminal.ansiBrightMagenta": pick(palette, "primaryFixedDim", primary),
      "terminal.ansiBrightCyan": pick(palette, "tertiaryFixedDim", tertiary),
      "terminal.ansiBrightWhite": pick(palette, "onSurface", foreground)
    },
    tokenColors: [
      {
        name: "Comment",
        scope: ["comment", "punctuation.definition.comment"],
        settings: {
          foreground: outline
        }
      },
      {
        name: "String",
        scope: ["string", "constant.other.symbol"],
        settings: {
          foreground: secondary
        }
      },
      {
        name: "Keyword",
        scope: ["keyword", "storage", "storage.type"],
        settings: {
          foreground: primary
        }
      },
      {
        name: "Function",
        scope: ["entity.name.function", "support.function", "meta.function-call"],
        settings: {
          foreground: tertiary
        }
      },
      {
        name: "Variable",
        scope: ["variable", "identifier"],
        settings: {
          foreground: tertiaryDim
        }
      },
      {
        name: "Constant",
        scope: ["constant", "entity.name.constant"],
        settings: {
          foreground: error
        }
      },
      {
        name: "Class and Type",
        scope: ["entity.name.type", "entity.name.class", "support.class"],
        settings: {
          foreground: pick(palette, "primaryFixedDim", primary)
        }
      },
      {
        name: "Number",
        scope: ["constant.numeric"],
        settings: {
          foreground: pick(palette, "secondaryFixedDim", secondary)
        }
      }
    ]
  };
}

async function main() {
  const raw = await readFile(colorsFile, "utf8");
  const parsed = JSON.parse(raw);
  const palette = parsed.dark ?? parsed.light;

  if (!palette) {
    throw new Error("colors.json must contain either a dark or light palette.");
  }

  const theme = buildTheme(palette);
  await writeFile(outputFile, `${JSON.stringify(theme, null, 2)}\n`, "utf8");
  process.stdout.write(`Generated ${path.relative(rootDir, outputFile)} from themes/colors.json\n`);
}

main().catch((error) => {
  process.stderr.write(`${error instanceof Error ? error.message : String(error)}\n`);
  process.exit(1);
});
