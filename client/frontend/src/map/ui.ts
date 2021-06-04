import { DataSet } from 'vis-data';
import { Network } from 'vis-network';
import { EmulatorNetwork, EmulatorNode } from '../common/types';
import { DataSource, Edge, Vertex } from './datasource';

export interface MapUiConfiguration {
    datasource: DataSource,
    mapElementId: string,
    infoPlateElementId: string,
    filterInputElementId: string,
    filterWrapElementId: string,
    logBodyElementId: string,
    logViewportElementId: string,
    logControls: {
        clearButtonElementId: string,
        autoscrollCheckboxElementId: string,
        disableCheckboxElementId: string
    }
}

export class MapUi {
    private _mapElement: HTMLElement;
    private _infoPlateElement: HTMLElement;
    private _filterInput: HTMLInputElement;
    private _filterWrap: HTMLElement;

    private _logView: HTMLElement;
    private _logBody: HTMLElement;
    private _logAutoscroll: HTMLInputElement;
    private _logDisable: HTMLInputElement;
    private _logClear: HTMLElement;

    private _datasource: DataSource;

    private _nodes: DataSet<Vertex, 'id'>;
    private _edges: DataSet<Edge, 'id'>;
    private _graph: Network;

    private _logQueue: HTMLElement[];

    private _flashQueue: Set<string>;
    private _flashingNodes: Set<string>;
    
    private _logPrinter: number;
    private _flasher: number;

    private _freezed: boolean;
    private _blocked: boolean;

    private _macMapping: { [mac: string]: string };

    constructor(config: MapUiConfiguration) {
        this._datasource = config.datasource;
        this._mapElement = document.getElementById(config.mapElementId);
        this._infoPlateElement = document.getElementById(config.infoPlateElementId);
        this._filterInput = document.getElementById(config.filterInputElementId) as HTMLInputElement;
        this._filterWrap = document.getElementById(config.filterWrapElementId);

        this._logView = document.getElementById(config.logViewportElementId);
        this._logBody = document.getElementById(config.logBodyElementId);
        this._logAutoscroll = document.getElementById(config.logControls.autoscrollCheckboxElementId) as HTMLInputElement;
        this._logDisable = document.getElementById(config.logControls.disableCheckboxElementId) as HTMLInputElement;
        this._logClear = document.getElementById(config.logControls.clearButtonElementId);

        this._freezed = false;

        this._logQueue = [];

        this._flashQueue = new Set<string>();
        this._flashingNodes = new Set<string>();

        this._macMapping = {};

        this._logClear.onclick = () => {
            this._logBody.innerText = '';
        };

        this._datasource.on('packet', (data) => {
            if (!data.source || !data.data) {
                return;
            }

            this._unfreeze();

            var flashed = new Set<string>();

            Object.keys(this._macMapping).forEach(mac => {
                if (data.data.includes(mac) && !flashed.has(mac)) {
                    flashed.add(mac);
                    this._flashQueue.add(this._macMapping[mac]);
                }
            });

            if (flashed.size > 0) {
                this._flashQueue.add(data.source);
            }

            // fixme?
            if (data.data.includes('listening')) {
                this._filterInput.classList.remove('error');
                this._filterWrap.classList.remove('error');
            }

            if (data.data.includes('error')) { 
                this._filterInput.classList.add('error');
                this._filterWrap.classList.add('error');
            }

            if (this._logDisable.checked) {
                return;
            }

            let node = this._nodes.get(data.source as string);

            let now = new Date();
            let timeString = `${now.getHours()}:${now.getMinutes()}:${now.getSeconds()}.${now.getMilliseconds()}`;

            let tr = document.createElement('tr');

            let td0 = document.createElement('td');
            let td1 = document.createElement('td');
            let td2 = document.createElement('td');

            td0.innerText = timeString;
            
            let a = document.createElement('a');

            a.href = '#';
            a.innerText = node.label;
            a.onclick = () => {
                this._updateInfoPlateWith(node.id);
                this._graph.selectNodes([node.id]);
            };

            td1.appendChild(a);

            td2.innerText = data.data;

            tr.appendChild(td0);
            tr.appendChild(td1);
            tr.appendChild(td2);

            this._logQueue.push(tr);
        });
    }

    private _randomColor() {
        return `hsl(${Math.random() * 360}, 100%, 75%)`;
    }

    private _flashNodes() {
        if (this._flashingNodes.size != 0) {
            // some nodes still flashing; wait for next time
            return;
        }

        this._flashingNodes = new Set(this._flashQueue);
        this._flashQueue.clear();

        let updateRequest = Array.from(this._flashingNodes).map(nodeId => {
            return {
                id: nodeId, borderWidth: 4
            }
        });

        this._nodes.update(updateRequest);

        // schedule un-flash
        window.setTimeout(() => {
            let updateRequest = Array.from(this._flashingNodes).map(nodeId => {
                return {
                    id: nodeId, borderWidth: 1
                }
            });

            this._nodes.update(updateRequest);
            this._flashingNodes.clear();
        }, 300);
    }

    private _freeze() {
        if (this._freezed) return;

        this._freezed = true;
        this._filterInput.disabled = true;
        this._filterInput.classList.add('disabled');
        this._filterWrap.classList.add('disabled');
    }

    private _unfreeze() {
        if (!this._freezed || this._blocked) return;

        this._freezed = false;
        this._filterInput.disabled = false;
        this._filterInput.classList.remove('disabled');
        this._filterWrap.classList.remove('disabled');
    }

    private async _filterUpdateHandler(event: KeyboardEvent) {
        if (event.key != 'Enter') return;

        this._blocked = true;
        this._freeze();
        this._filterInput.value = await this._datasource.setSniffFilter(this._filterInput.value);
        this._blocked = false;
    }

    private _createInfoPlateValuePair(label: string, text: string): HTMLDivElement {
        let div = document.createElement('div');

        let span0 = document.createElement('span');
        span0.className = 'label';
        span0.innerText = label;

        let span1 = document.createElement('span');
        span1.className = 'text';
        span1.innerText = text;

        div.appendChild(span0);
        div.appendChild(span1);

        return div;
    }

    private _updateInfoPlateWith(nodeId: string) {
        let vertex = this._nodes.get(nodeId);

        this._infoPlateElement.innerText = '';

        let title = document.createElement('div');
        title.className = 'title';
        this._infoPlateElement.appendChild(title);

        if (vertex.type == 'network') {
            let net = vertex.object as EmulatorNetwork;
            title.innerText = `${net.meta.emulatorInfo.type == 'global' ? 'Exchange' : 'Network'}: ${vertex.label}`;

            this._infoPlateElement.appendChild(this._createInfoPlateValuePair('ID', net.Id.substr(0, 12)));
            this._infoPlateElement.appendChild(this._createInfoPlateValuePair('Name', net.meta.emulatorInfo.name));
            this._infoPlateElement.appendChild(this._createInfoPlateValuePair('Scope', net.meta.emulatorInfo.scope));
            this._infoPlateElement.appendChild(this._createInfoPlateValuePair('Type', net.meta.emulatorInfo.type));
            this._infoPlateElement.appendChild(this._createInfoPlateValuePair('Prefix', net.meta.emulatorInfo.prefix));
        }

        if (vertex.type == 'node') {
            let node = vertex.object as EmulatorNode;
            title.innerText = `${node.meta.emulatorInfo.role == 'Router' ? 'Router' : 'Host'}: ${vertex.label}`;

            this._infoPlateElement.appendChild(this._createInfoPlateValuePair('ID', node.Id.substr(0, 12)));
            this._infoPlateElement.appendChild(this._createInfoPlateValuePair('ASN', node.meta.emulatorInfo.asn.toString()));
            this._infoPlateElement.appendChild(this._createInfoPlateValuePair('Name', node.meta.emulatorInfo.name));
            this._infoPlateElement.appendChild(this._createInfoPlateValuePair('Role', node.meta.emulatorInfo.role));

            node.meta.emulatorInfo.nets.forEach(net => {
                this._infoPlateElement.appendChild(this._createInfoPlateValuePair(`IP(${net.name})`, net.address));
            });

            let consoleLink = document.createElement('a');
            
            consoleLink.target = '_blank';
            consoleLink.href = `/console.html#${node.Id.substr(0, 12)}`;
            consoleLink.innerText = 'Launch console';

            this._infoPlateElement.appendChild(consoleLink);
        }
    }

    private _mapMacAddresses() {
        this._nodes.forEach(vertex => {
            if (vertex.type != 'node') {
                return;
            }

            let node = vertex.object as EmulatorNode;

            Object.keys(node.NetworkSettings.Networks).forEach(key => {
                let net = node.NetworkSettings.Networks[key];
                this._macMapping[net.MacAddress] = net.NetworkID;
            });
        });
    }

    private _boundfilterUpdateHandler = this._filterUpdateHandler.bind(this);

    async start() {
        await this._datasource.connect();
        this.redraw();
        this._mapMacAddresses();
        this._filterInput.value = await this._datasource.getSniffFilter();
        this._filterInput.addEventListener('keydown', this._boundfilterUpdateHandler);

        this._logPrinter = window.setInterval(() => {
            var scroll = false;

            while (this._logQueue.length > 0) {
                scroll = true;
                this._logBody.appendChild(this._logQueue.shift());
            }

            if (scroll && this._logAutoscroll.checked && !this._logDisable.checked) {
                this._logView.scrollTop = this._logView.scrollHeight;
            }
        }, 500);

        this._flasher = window.setInterval(() => {
            this._flashNodes();
        }, 500);
    }

    stop() {
        this._datasource.disconnect();
        this._filterInput.removeEventListener('keydown', this._boundfilterUpdateHandler);
        window.clearInterval(this._logPrinter);
        window.clearInterval(this._flasher);
    }

    redraw() {
        this._edges = new DataSet(this._datasource.edges);
        this._nodes = new DataSet(this._datasource.vertices);

        var groups = {};

        this._datasource.groups.forEach(group => {
            groups[group] = {
                color: {
                    border: '#000',
                    background: this._randomColor()
                }
            }
        });

        this._graph = new Network(this._mapElement, {
            nodes: this._nodes,
            edges: this._edges
        }, {
            groups
        });

        this._graph.on('click', (ev) => {
            if (ev.nodes.length <= 0) return;
            this._updateInfoPlateWith(ev.nodes[0]);            
        });
    }
}