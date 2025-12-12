import type {Vertex, Edge} from "@/utils/map-datasource.ts";
import {MapUi as BaseMapUi, type MapUiConfiguration} from "@/utils/map-ui.ts";
import {DataSource} from './datasource.ts';
import type {Ref} from "vue";
export interface IxMapUiOtherConfiguration {
    settingControls: {
        ixNumberValue: Ref<number>,
        ixNumberMaxValue: Ref<number>,
    },
}

/**
 * map UI controller.
 */
export class MapUi extends BaseMapUi {
    private _ixNumber: Ref<number>;
    private _ixNumberMax: Ref<number>;
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
    }

    getDataSetOrigin() {
        return this._datasource.visDataSet(this._datasource.ixs.length)
    }

    setIXNumber() {
        this._ixNumber.value = this._datasource.ixs.length
        this._ixNumberMax.value = this._datasource.ixs.length
    }

    async start() {
        await super.start()
        this.setIXNumber()
        this.allLoadingInstance?.close()
    }

    onIXNumChange(currentValue: number) {
        const {_nodes, _edges, _graph} = this.getter();

        const {vertices, edges} = this._datasource.visDataSet(currentValue)
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
        _graph.stabilize();
    }
}
