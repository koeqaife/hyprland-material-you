const entry = App.configDir + "/main.ts";
const outdir = "/tmp/ags/js";

App.addIcons(`${App.configDir}/assets/icons`);

try {
    // prettier-ignore
    await Utils.execAsync([
        "bun", "build", entry,
        "--outdir", outdir,
        "--external", "resource://*",
        "--external", "gi://*"
    ]);
    await import(`file://${outdir}/main.js`);
} catch (error) {
    console.error(error);
}

export {};
