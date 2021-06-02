import { DataSet } from 'vis-data';
import { Network } from 'vis-network';
import { DataSource, Edge, Vertex } from './datasource';

export interface MapUiConfiguration {
    datasource: DataSource,
    mapElementId: string,
    infoPlateElementId: string
}

export class MapUi {
    private _mapElement: HTMLElement;
    private _infoPlateElement: HTMLElement;
    private _datasource: DataSource;

    private _nodes: DataSet<Vertex, 'id'>;
    private _edges: DataSet<Edge, 'id'>;

    constructor(config: MapUiConfiguration) {
        this._datasource = config.datasource;
        this._mapElement = document.getElementById(config.mapElementId);
        this._infoPlateElement = document.getElementById(config.infoPlateElementId);

        this._datasource.on('packet', (data) => {
            if (data.source) {
                this._flashNode(data.source);
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