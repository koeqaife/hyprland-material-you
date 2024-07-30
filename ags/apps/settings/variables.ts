import { Variable as VariableType } from "types/variable";

export let current_window;
export function set_current_window(value: any) {
    current_window = value;
}

export const current_tab = Variable("network");
export const saved_networks: VariableType<string[]> = Variable([], {
    poll: [
        5000,
        () => {
            if (current_tab.value != "network" || !current_window?.visible) return saved_networks?.value || [];
            const _saved = Utils.exec(`${App.configDir}/scripts/network.sh --saved`);
            return _saved.split("\n");
        }
    ]
});
