export type Message = {
    success: boolean;
    message?: string;
    rate_limit?: true;
};

export type ChatMessage = {
    created_at: string;
    id: number;
    message: string;
    nickname: string;
    type: number;
};

export type LastMessages = Message & {
    messages?: ChatMessage[];
};

export type CreateRoom = Message & {
    key: string;
    id: string;
};

export type GetRoom = Message & {
    key: string | null;
    id: string | null;
};

export type CreateUser = Message & {
    wait_for_accept: boolean
};
export type CheckUser = Message;
export type SendMessage = Message & ChatMessage;
export type Online = Message;
export type OnlineMember = {
    nickname: string;
    timestamp: number;
};
export type OnlineList = Message & {
    hidden?: boolean;
    online?: OnlineMember[];
    online_count?: number;
};

export type GetInfo = Message & {
    max_rate_limit: number;
    version: number;
} & {
    [key: string]: any;
};

export type RequestParams = {
    url: string;
    method?: "get" | "post" | "put" | "delete";
    json?: string;
    headers?: string;
};

export type RequestReturn<T> = {
    code: number;
    data: T;
    type: "text" | "json";
};
