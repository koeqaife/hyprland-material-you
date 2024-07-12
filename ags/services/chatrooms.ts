import GLib from "gi://GLib";
import type * as Types from "./chatroom.d.ts";

const requests = `${App.configDir}/scripts/requests.py`;

const default_config = {
    ip: "",
    room: "",
    username: ""
};

async function send_request<T>({
    url,
    method = "get",
    json = undefined,
    headers = undefined
}: Types.RequestParams): Promise<Types.RequestReturn<T>> {
    let command = ["python", "-O", requests, `--${method}`, url];
    if (json) command = [...command, "--json", json];
    if (headers) command = [...command, "--headers", headers];
    const r = await Utils.execAsync(command);
    const response: Types.RequestReturn<T> = JSON.parse(r);
    return response;
}

class ChatroomsService extends Service {
    static {
        Service.register(
            this,
            {
                "room-changed": ["boolean"],
                "ip-changed": ["boolean"],
                "new-messages": ["jsobject"],
                "version-mismatch": ["boolean"]
            },
            {
                ip: ["string", "rw"],
                messages: ["jsobject", "r"],
                online: ["jsobject", "r"],
                last_error: ["string", "r"],
                username: ["string", "r"],
                login_success: ["boolean", "rw"]
            }
        );
    }

    #ip = ``;
    #config_file = `${GLib.get_user_state_dir()}/ags/user/chatrooms.json`;
    #config = default_config;
    #room = "none";
    #messages: Types.ChatMessage[] = [];
    #online: Types.OnlineMember[] = [];
    #username = "mrdan";
    #password = "test";
    #login_success = false;
    #last_error = "";
    #server_version = 6;
    #info_checked = false;
    #get_messages_lock = false;

    get ip() {
        return this.#ip;
    }

    set ip(value) {
        this.#ip = value;
        this.#login_success = false;
        this.#info_checked = false;
        this.#set_config("ip", value);
        this.notify("ip");
        this.emit("ip-changed", true);
        this.#check_server().catch(print);
    }

    get messages() {
        return this.#messages;
    }

    get login_success() {
        return this.#login_success;
    }

    set login_success(value) {
        if (!value) {
            this.#login_success = false;
            this.notify("login_success");
            this.#username = "";
            this.#password = "";
        }
    }

    get online() {
        return this.#online;
    }

    get last_error() {
        return this.#last_error;
    }

    get username() {
        return this.#username;
    }

    async #check_server() {
        const r = await send_request<Types.GetInfo>({
            url: `${this.#ip}/info`,
            method: "get"
        });
        if (r.data.version != this.#server_version) {
            this.#set_last_error("The server version is different from the supported version");
            this.emit("version-mismatch", true);
        } else this.#info_checked = true;
        return {
            mismatch: r.data.version != this.#server_version,
            response: r
        };
    }

    #set_last_error(value: string) {
        this.#last_error = value;
        this.notify("last_error");
        this.emit("changed");
    }

    #set_config(key: keyof typeof default_config, value: string) {
        const config = { ...this.#config, [key]: value };
        Utils.writeFile(JSON.stringify(config), this.#config_file).catch(print);
    }

    #on_change_room() {
        this.#messages = [];
        this.#online = [];
        this.emit("changed");
        this.emit("room-changed", true);
    }

    async set_room(room_key: string) {
        this.#login_success = false;

        const headers = {
            room: room_key
        };

        const r = await send_request<Types.GetRoom>({
            url: `${this.#ip}/get_room`,
            method: "get",
            headers: JSON.stringify(headers)
        });
        if (r.code == 200 && r.data.success) {
            this.#room = room_key;
            this.#on_change_room();
            this.#set_config("room", this.#room);
        } else if (r.data.message) {
            this.#set_last_error(r.data.message);
        }
        return r;
    }

    async create_room() {
        this.#login_success = false;

        const r = await send_request<Types.CreateRoom>({
            url: `${this.#ip}/create_room`,
            method: "post"
        });
        if (r.code == 200 && r.data.success) {
            this.#room = r.data.key;
            this.#on_change_room();
            this.#set_config("room", this.#room);
        } else if (r.data.message) {
            this.#set_last_error(r.data.message);
        }
        return r;
    }

    async send_message(message: string) {
        const data = {
            username: this.#username,
            password: this.#password,
            text: message
        };

        const headers = {
            room: this.#room,
            "Content-Type": `application/json`
        };

        const r = await send_request<Types.SendMessage>({
            url: `${this.#ip}/send_message`,
            method: "post",
            json: JSON.stringify(data),
            headers: JSON.stringify(headers)
        });
        if (r.code == 200 && r.data.success) {
            let message = r.data;
            if (r.data.id == -1) message.id = this.#messages.at(-1)?.id || 0;
            this.#messages = [...this.#messages, message];
            this.emit("changed");
            this.notify("messages");

            this.emit("new-messages", [message]);
        } else if (r.data.message) {
            this.#set_last_error(r.data.message);
        }
        return r;
    }

    async create_user(username: string, password: string) {
        this.#login_success = false;

        const data = {
            username: username,
            password: password
        };

        const headers = {
            room: this.#room,
            "Content-Type": `application/json`
        };

        const r = await send_request<Types.CreateUser>({
            url: `${this.#ip}/create_user`,
            method: "post",
            json: JSON.stringify(data),
            headers: JSON.stringify(headers)
        });
        if (r.code == 200 && r.data.success) {
            this.#username = username;
            this.#password = password;
            if (r.data.wait_for_accept)
                this.#set_last_error(
                    "Your account has been successfully created but you need to wait for the chatroom owner to allow you to log in"
                );
            else this.#login_success = true;
        } else if (r.data.message) {
            this.#set_last_error(r.data.message);
        }
        return r;
    }

    async login(username: string, password: string) {
        this.#login_success = false;

        const data = {
            username: username,
            password: password
        };

        const headers = {
            room: this.#room,
            "Content-Type": `application/json`
        };

        const r = await send_request<Types.CheckUser>({
            url: `${this.#ip}/check_user`,
            method: "get",
            json: JSON.stringify(data),
            headers: JSON.stringify(headers)
        });
        if (r.code == 200 && r.data.success) {
            this.#username = username;
            this.#password = password;
            this.#login_success = true;
            this.#set_config("username", username);
        } else if (r.data.message) {
            this.#set_last_error(r.data.message);
        }
        return r;
    }

    constructor() {
        super();

        Utils.exec(["mkdir", "-p", `${GLib.get_user_state_dir()}/ags/user/`]);
        const config_file = this.#config_file;
        if (Utils.readFile(config_file).length < 2) {
            Utils.writeFileSync(JSON.stringify(default_config), config_file);
        }
        Utils.readFileAsync(this.#config_file)
            .then((out) => {
                this.#config = { ...default_config, ...JSON.parse(out) };
                if (this.#config?.ip && this.#config?.ip?.length > 0) {
                    this.ip = this.#config["ip"];
                    this.set_room(this.#config["room"]).catch(print);
                }
                this.#username = this.#config["username"];
                this.notify("username");
                this.emit("changed");
            })
            .catch(print);
        Utils.interval(1500, () => {
            if (this.#login_success && !this.#get_messages_lock) {
                if (!this.#info_checked)
                    this.#check_server()
                        .then((out) => {
                            if (!out.mismatch) {
                                this.#get_messages();
                            }
                        })
                        .catch(print);
                else {
                    this.#get_messages();
                }
            }
        });
    }

    #get_messages() {
        this.#get_messages_lock = true;
        const data = {
            username: this.#username,
            password: this.#password,
            after_message: this.#messages.at(-1)?.id || 0
        };

        const headers = {
            room: this.#room,
            "Content-Type": `application/json`
        };
        send_request<Types.LastMessages>({
            url: `${this.#ip}/get_last_messages`,
            method: `get`,
            json: JSON.stringify(data),
            headers: JSON.stringify(headers)
        })
            .then((r) => {
                if (r.code == 200 && r.data["success"]) {
                    if (r.data.messages?.length || 0 > 0) {
                        this.#messages = [...this.#messages, ...r.data.messages!];
                        this.emit("changed");
                        this.notify("messages");

                        this.emit("new-messages", r.data.messages);
                    }
                } else {
                    print(r.code, r.type == "json" ? JSON.stringify(r.data) : r.data);
                }
            })
            .catch(() => {})
            .finally(() => {
                this.#get_messages_lock = false;
            });
    }

    connect(event = "room-changed", callback) {
        return super.connect(event, callback);
    }
}

const chatrooms = new ChatroomsService();

export { chatrooms };
