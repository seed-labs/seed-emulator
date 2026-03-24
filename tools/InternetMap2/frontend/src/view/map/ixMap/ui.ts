import type {Vertex, Edge} from "@/utils/map-datasource.ts";
import {MapUi as BaseMapUi, type MapUiConfiguration} from "@/utils/map-ui.ts";
import {DataSource} from './datasource.ts';
import type {Ref} from "vue";
import {allLoading} from "@/utils/tools.ts";
import {DataSet} from "vis-data";

export interface IxMapUiOtherConfiguration {
    settingControls: {
        ixNumberValue: Ref<number>,
        ixNumberMaxValue: Ref<number>,
        ixOptions: Ref<any>,
    },
}

/**
 * map UI controller.
 */
export class MapUi extends BaseMapUi {
    private _ixNumber: Ref<number>;
    private _ixNumberMax: Ref<number>;
    private _ixOptions: Ref<any>;
    protected _datasource: DataSource;

    /**
     * Build a new map UI controller.
     *
     * @param config element bindings.
     * @param ixConfig
     */
    constructor(config: MapUiConfiguration, ixConfig: IxMapUiOtherConfiguration) {
        super(config)
        this._datasource = config.datasource as DataSource;
        this._ixNumber = ixConfig.settingControls.ixNumberValue;
        this._ixNumberMax = ixConfig.settingControls.ixNumberMaxValue;
        this._ixOptions = ixConfig.settingControls.ixOptions
    }

    getDataSetOrigin() {
        return this._datasource.visDataSet(this._datasource.ixs.length)
    }

    setIXNumber() {
        this._ixNumber.value = this._datasource.ixs.length
        this._ixNumberMax.value = this._datasource.ixs.length
        this._ixOptions.value = this._datasource.ixs.map(ix => {
            return {
                label: ix.meta.emulatorInfo.displayname,
                value: ix.meta.emulatorInfo.name,
            }
        })
    }

    async start() {
        await super.start()
        this.setIXNumber()
    }

    async partStart(): Promise<void> {
        await super.partStart()
        const {vertices, edges} = this.getDataSetOrigin()
        this._edges = new DataSet(edges);
        this._nodes = new DataSet(vertices);
        this.setIXNumber()
    }

    onIXNumChange(currentValue: number) {
        const {vertices, edges} = this._datasource.visDataSet(currentValue)
        this._updateMap(vertices, edges)
    }

    onIXBlur(currentValue: string[]) {
        const {vertices, edges} = this._datasource.visDataSetByIX(currentValue)
        this._updateMap(vertices, edges)
    }

    _updateMap(vertices: Vertex[], edges: Edge[]) {
        const {_nodes, _edges, _graph} = this.getter();
        this.allLoadingInstance = allLoading()
        try {
            vertices.filter(item => !_nodes.get(item.id)).forEach((item: Vertex) => {
                _nodes.add(item)
            })
            _nodes.remove(_nodes.get({
                filter: (item: Vertex) => !vertices.filter(_item => _item.id === item.id).length
            }).map((item: Vertex) => item.id))
            _edges.remove(_edges.get({
                filter: (item: Edge) => !edges.filter(_item => _item.from === item.from && _item.to === item.to).length
            }).map((item: Edge) => item.id!))
            edges.filter((item: Edge) => !_edges.get({
                filter: (_item: Edge) => _item.from === item.from && _item.to === item.to
            }).length).forEach((edge: Edge) => {
                _edges.add(edge)
            })
            if (!this._graph) {
                this.createVisGraph()
            } else {
                this._graph.stabilize();
            }
        } catch (e) {
            console.log(e)
        }
        this.allLoadingInstance?.close()
    }
}
