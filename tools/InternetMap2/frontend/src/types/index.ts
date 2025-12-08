export interface NewRouteRecord {
    title: string | undefined,
    name: string,
    content: string,
    icon: string | undefined,
    type?: 'element' | undefined,
}

export interface RouteRecord {
    path: string;
    component?: () => Promise<any>;
    name?: string;
    redirect?: { name: string };
    meta?: {
        title: string;
        icon?: string;
        componentName?: string | undefined;
    };
    children?: RouteRecord[];
}

export interface Response {
    status: boolean;
    data: { data: any[]; };
    message: string;
}

export interface Details {
    title: string,
    data: { [key: string]: string | string[]}
}

export interface HoverNodeEvent {
    node: string;
    pointer: {
        DOM: { x: number; y: number; };
        canvas: { x: number; y: number; };
    };
    event: MouseEvent;
}