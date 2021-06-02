import { DataSet } from 'vis-data';
import { Network } from 'vis-network';
import { DataSource, Edge, Vertex } from './datasource';

export interface MapUiConfiguration {
    datasource: DataSource,
    mapElementId: string,
    infoPlateElementId: string,
    filterInputElementId: string,
    filterWrapElementId: string
}

export class MapUi {
    private _mapElement: HTMLElement;
    private _infoPlateElement: HTMLElement;
    private _filterInput: HTMLInputElement;
    private _filterWrap: HTMLElement;
    private _datasource: DataSource;

    private _nodes: DataSet<Vertex, 'id'>;
    private _edges: DataSet<Edge, 'id'>;

    private _freezed: boolean;
    private _blocked: boolean;

    constructor(config: MapUiConfiguration) {
        this._datasource = config.datasource;
        this._mapElement = document.getElementById(config.mapElementId);
        this._infoPlateElement = document.getElementById(config.infoPlateElementId);
        this._filterInput = document.getElementById(config.filterInputElementId) as HTMLInputElement;
        this._filterWrap = document.getElementById(config.filterWrapElementId);

        this._freezed = false;

        this._datasource.on('packet', (data) => {
            this._unfreeze();

            if (data.source) {
                this._flashNode(data.source);
            }

            // fixme?
            if (data.data) {
                if (data.data.includes('listening')) {
                    this._filterInput.classList.remove('error');
                    this._filterWrap.classList.remove('error');
                }

                if (data.data.includes('error')) { 
                    this._filterInput.classList.add('error');
                    this._filterWrap.classList.add('error');
                }
            }
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

    private _boundfilterUpdateHandler = this._filterUpdateHandler.bind(this);

    async start() {
        this.redraw();
        this._filterInput.value = await this._datasource.getSniffFilter();
        this._filterInput.addEventListener('keydown', this._boundfilterUpdateHandler);
    }

    stop() {
        this._datasource.disconnect();
        this._filterInput.removeEventListener('keydown', this._boundfilterUpdateHandler);
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

        var graph = new Network(this._mapElement, {
            nodes: this._nodes,
            edges: this._edges
        }, {
            groups
        });

        graph.on('click', (ev) => {
            if (ev.nodes.length <= 0) return;
            let node = ev.nodes[0];

            // todo
        });
    }
}