import * as fs from 'fs';
import * as path from 'path';
import {Logger} from 'tslog';
import dockerode from 'dockerode';
import {LogProducer} from "../interfaces/log-producer";

export interface IPlugin {
    id: string;
    name: string;
    version: string;
    entryPoint: string;
    description?: string;
    activate?: () => void;
    deactivate?: () => void;
}

export class PluginManager implements LogProducer {
    private readonly _logger: Logger;
    private _docker: dockerode;
    public plugins: IPlugin[] = [];
    private readonly _pluginDirs: string[];

    constructor(docker: dockerode, pluginDirs: string[] = ['../plugin'], namespace: String = '') {
        this._docker = docker;
        this._pluginDirs = pluginDirs.map(pluginDir => path.resolve(pluginDir));
        this._logger = new Logger({name: `${namespace}PluginManager`});
        this.discoverPlugins().then(r => {
        })
    }

    private async discoverPlugins(): Promise<IPlugin[]> {
        for (const pluginDir of this._pluginDirs) {
            if (!fs.existsSync(pluginDir)) {
                return
            }

            const items = fs.readdirSync(pluginDir, {withFileTypes: true});
            for (const item of items) {
                if (item.isDirectory()) {
                    const pluginPath = path.join(pluginDir, item.name);
                    const manifestPath = path.join(pluginPath, 'plugin.json');

                    if (fs.existsSync(manifestPath)) {
                        try {
                            const manifest = JSON.parse(fs.readFileSync(manifestPath, 'utf8'));
                            const plugin = await this.loadPlugin(pluginPath, manifest);
                            this.plugins.push(plugin);
                        } catch (error) {
                            console.error(`Failed to load plugin ${item.name}:`, error);
                        }
                    }
                }
            }
        }
    }

    private async loadPlugin(pluginPath: string, manifest: any): Promise<IPlugin> {
        // const entryPoint = path.join(pluginPath, manifest.entryPoint);

        // const pluginModule = await import(entryPoint);
        // const pluginInstance = pluginModule.default || pluginModule;

        return {
            id: manifest.id,
            name: manifest.name,
            version: manifest.version,
            entryPoint: manifest.entryPoint,
            description: manifest.description,
            // activate: pluginInstance.activate,
            // deactivate: pluginInstance.deactivate
        };
    }

    activateAll(): void {
        this.plugins.forEach(plugin => {
            try {
                plugin.activate();
                console.log(`Plugin ${plugin.name} activated`);
            } catch (error) {
                console.error(`Failed to activate plugin ${plugin.name}:`, error);
            }
        });
    }

    getLoggers(): Logger[] {
        return [this._logger];
    }
}