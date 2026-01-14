import type {Vertex, Edge} from "@/utils/map-datasource.ts";
import {MapUi as BaseMapUi, type MapUiConfiguration} from "@/utils/map-ui.ts";
import {DataSource} from './datasource.ts';
import type {Ref} from "vue";
import {allLoading} from "@/utils/tools.ts";
import type {TransitsEmulatorNodeInfo} from "@/utils/types.ts";

export interface TransitMapUiOtherConfiguration {
    settingControls: {
        transitNumberValue: Ref<number>,
        transitNumberMaxValue: Ref<number>,
        transits: Ref<TransitsEmulatorNodeInfo[]>,
        transitsCheckedList: Ref<number[]>,
    },
}

/**
 * map UI controller.
 */
export class MapUi extends BaseMapUi {
    private _transitNumber: Ref<number>;
    private _transitNumberMax: Ref<number>;
    private _transits: Ref<TransitsEmulatorNodeInfo[]>;
    private _transitsCheckedList: Ref<number[]>;
    protected _datasource: DataSource;

    /**
     * Build a new map UI controller.
     *
     * @param config element bindings.
     * @param transitConfig
     */
    constructor(config: MapUiConfiguration, transitConfig: TransitMapUiOtherConfiguration) {
        super(config)
        this._datasource = config.datasource as DataSource;
        this._transitNumber = transitConfig.settingControls.transitNumberValue;
        this._transitNumberMax = transitConfig.settingControls.transitNumberMaxValue;
        this._transits = transitConfig.settingControls.transits;
        this._transitsCheckedList = transitConfig.settingControls.transitsCheckedList;
    }

    getDataSetOrigin() {
        return this._datasource.visDataSet(this._datasource.transits.length)
    }

    setTransitNumber() {
        this._transitNumber.value = this._datasource.transits.length
        this._transitNumberMax.value = this._datasource.transits.length
        this._transits.value = this._datasource.transits
        this._transitsCheckedList.value = this._datasource.transits.map((item: TransitsEmulatorNodeInfo) => item.asn)
    }

    async start() {
        await super.start()
        this.setTransitNumber()
    }

    onTransitNumChange(currentValue: number) {
        const {vertices, edges} = this._datasource.visDataSet(currentValue)
        this._updateTransitMap(vertices, edges)
    }

    onTransitsCheckedChange(currentValue: number[]) {
        const {vertices, edges} = this._datasource.visDataSetByAsn(currentValue)
        this._updateTransitMap(vertices, edges)
    }

    onTransitsCheckAllChange(currentValue: boolean) {
        if (currentValue) {
            const {vertices, edges} = this._datasource.visDataSet(this._datasource.transits.length)
            this._updateTransitMap(vertices, edges)
        } else {
            this._updateTransitMap([], [])
        }
    }

    _updateTransitMap(vertices: Vertex[], edges: Edge[]) {
        this.allLoadingInstance = allLoading()

        const {_nodes, _edges, _graph} = this.getter();
        vertices.filter(item => !_nodes.get(item.id)).forEach((item: Vertex) => {
            _nodes.add(item)
        })
        let updateHidden = _nodes.get({
            filter: item => vertices.some(v => v.id === item.id && item.hidden)
        }).map(item => ({id: item.id, hidden: false}))
        _nodes.update(updateHidden)

        // _nodes.remove(_nodes.get({
        //     filter: (item: Vertex) => !vertices.filter(_item => _item.id === item.id).length
        // }).map((item: Vertex) => item.id))
        updateHidden = _nodes.get({
            filter: (item: Vertex) => !vertices.filter(_item => _item.id === item.id).length
        }).map((item: Vertex) => ({id: item.id, hidden: true}))
        _nodes.update(updateHidden)

        _edges.remove(_edges.get({
            filter: (item: Edge) => !edges.some(_item => _item.from === item.from && _item.to === item.to)
        }).map((item: Edge) => item.id!))

        edges.filter((item: Edge) => !_edges.get({
            filter: (_item: Edge) => _item.from === item.from && _item.to === item.to
        }).length).forEach((edge: Edge) => {
            _edges.add(edge)
        })
        _graph.stabilize();

        this.allLoadingInstance?.close()
    }
}
