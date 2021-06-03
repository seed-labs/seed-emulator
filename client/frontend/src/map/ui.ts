import { DataSet } from 'vis-data';
import { Network } from 'vis-network';
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
    private _logPrinter: number;

    private _freezed: boolean;
    private _blocked: boolean;

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

        this._logClear.onclick = () => {
            this._logBody.innerText = '';
        };

        this._datasource.on('packet', (data) => {
            if (!data.source || !data.data) {
                return;
            }

            this._unfreeze();

            this._flashNode(data.source);

            if (this._logDisable.checked) {
                return;
            }

            let node = this._nodes.get(data.source as string);

            // fixme?
            if (data.data.includes('listening')) {
                this._filterInput.classList.remove('error');
                this._filterWrap.classList.remove('error');
            }

            if (data.data.includes('error')) { 
                this._filterInput.classList.add('error');
                this._filterWrap.classList.add('error');
            }

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

    private _setNodeHighlight(id: string, highlight: boolean) {
        this._nodes.update({
            id: id, borderWidth: highlight ? 4 : 1
        });
    }

    private _flashNode(id: string) {
        this._setNodeHighlight(id, true);

        window.setTimeout(() => {
            this._setNodeHighlight(id, false);
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

    private _updateInfoPlateWith(nodeId: string) {
        // todo
    }

    private _boundfilterUpdateHandler = this._filterUpdateHandler.bind(this);

    async start() {
        this.redraw();
        this._filterInput.value = await this._datasource.getSniffFilter();
        this._filterInput.addEventListener('keydown', this._boundfilterUpdateHandler);
        this._logPrinter = window.setInterval(() => {
            while (this._logQueue.length > 0) {
                this._logBody.appendChild(this._logQueue.shift());
            }

            if (this._logAutoscroll.checked && !this._logDisable.checked) {
                this._logView.scrollTop = this._logView.scrollHeight;
            }
        }, 500);
    }

    stop() {
        this._datasource.disconnect();
        this._filterInput.removeEventListener('keydown', this._boundfilterUpdateHandler);
        window.clearInterval(this._logPrinter);
    }

    async redraw() {
        await this._datasource.connect();

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