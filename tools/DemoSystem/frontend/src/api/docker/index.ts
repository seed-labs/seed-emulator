import request from '@/utils/request'
import type {ApiResponse} from "@/api"

export const URL = {
    DOCKER_CONNECT_URL: '/docker/connect',
    DOCKER_EXEC_URL: '/docker/exec',
    HOST_EXEC_URL: '/docker/host/exec',
    DOCKER_COMPOSE_EXEC_URL: '/docker/compose/exec',
    DOCKER_EXEC_CP_URL: '/docker/exec/cp',
    DOCKER_EXEC_RENAME_URL: '/docker/exec/rename',
    DOCKER_EXEC_APPEND_TO_FILE_URL: '/docker/exec/append',
} as const


export const reqDockerConnect = (data: { host: string; port: string }): Promise<ApiResponse<any>> => {
    return request.post(
        URL.DOCKER_CONNECT_URL,
        data,
    )
}

export interface HostExec {
    cmd: string
}

export interface DockerExec {
    host: string;
    port: string;
    containerIds: string[];
    containerNames: string[];
    cmd: string
    detach?: boolean
}

export interface DockerExecCp {
    host: string;
    port: string;
    srcName: string,
    dstName: string,
    srcPath: string,
    dstPath: string,
}

export interface DockerComposeExec {
    host: string;
    port: string;
    composePath: string,
    cmd: string,
}

export interface DockerExecRename {
    host: string;
    port: string;
    containerIds: string[];
    containerNames: string[];
    oldPath: string,
    newPath: string
}

export interface DockerExecAppendToFile {
    host: string;
    port: string;
    containerIds: string[];
    containerNames: string[];
    filepath: string,
    content: string,
    signature: string,
}

export const reqHostExec = (data: HostExec): Promise<ApiResponse<any>> => {
    return request.post(
        URL.HOST_EXEC_URL,
        data,
    )
}

export const reqDockerExec = (data: DockerExec): Promise<ApiResponse<any>> => {
    return request.post(
        URL.DOCKER_EXEC_URL,
        data,
    )
}

export const reqDockerComposeExec = (data: DockerComposeExec): Promise<ApiResponse<any>> => {
    return request.post(
        URL.DOCKER_COMPOSE_EXEC_URL,
        data,
    )
}

export const reqDockerExecCp = (data: DockerExecCp): Promise<ApiResponse<any>> => {
    return request.post(
        URL.DOCKER_EXEC_CP_URL,
        data,
    )
}

export const reqDockerExecRename = (data: DockerExecRename): Promise<ApiResponse<any>> => {
    return request.post(
        URL.DOCKER_EXEC_RENAME_URL,
        data,
    )
}

export const reqDockerExecAppendToFile = (data: DockerExecAppendToFile): Promise<ApiResponse<any>> => {
    return request.post(
        URL.DOCKER_EXEC_APPEND_TO_FILE_URL,
        data,
    )
}
