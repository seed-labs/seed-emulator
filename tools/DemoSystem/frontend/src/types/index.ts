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

export interface BaseConsoleForm {
  name: string
  host: string
  port: string
}

// 定义不同子组件可能需要的特定表单类型
export interface BGPConsoleForm extends BaseConsoleForm {
  targetHost: string
  targetType: string
  targetIPs: string[]
}