import {DataSet} from 'vis-data';
import type {FullItem} from 'vis-data/declarations/data-interface';
import {Network, type NodeOptions, type Options} from 'vis-network';
import type {Ref} from "vue"
import {bpfCompletionTree} from './bpf';
import {Completion} from './completion';
import type {EmulatorNetwork, EmulatorNode} from './types';
import {WindowManager} from './window-manager';
import {DataSource, type NodesType, type EdgesType, type Vertex, META_CLASS, type Edge} from './map-datasource';
import {DataSource as IXDataSource} from "@/view/map/ixMap/datasource.ts";
import {DataSource as TransitDataSource} from "@/view/map/transitMap/datasource.ts";
import type {Details, HoverNodeEvent, IframeQueryData} from '@/types/index.ts'
import type {LoadingInstance} from 'element-plus/es/components/loading/src/loading';
import {allLoading} from "@/utils/tools.ts";


declare global {
    interface Window {
        __ENV__: {
            CONSOLE: string;
        };
    }
}
const CONSOLE = window.__ENV__?.CONSOLE;
const CLICK_DELAY = 250
const VIS_VERTEX_MAX = 300

export interface replayValueType {
    disabled: boolean,
    max?: number,
    value?: number,
}

export const CLICK_CLASS = {
    PEER_ACTION_CLASS: 'peer-action',
    CONSOLE_CLASS: 'console-action',
    NET_TOGGLE_CLASS: 'net-toggle-action',
    RELOAD_CLASS: 'reload-action',
}

/**
 * map UI element bindings.
 */
export interface MapUiConfiguration {
    datasource: DataSource | IXDataSource | TransitDataSource, // data provider
    mapElementId: string, // element id of the map
    detailsDialogVisible: Ref<boolean>,
    details: Ref<Details[]>,
    allService: Ref<string[]>,
    filterInputValue: Ref<string>,
    searchInputValue: Ref<string>,
    suggestionsElementId: string,
    logBodyElementId: string, // element id of the log body (the tbody)
    logPanelElementId: string, // element id of the log panel
    logViewportElementId: string, // element id of the log viewport (the table wrapper w/ overflow scroll)
    logWrapElementId: string, // element id of the log wrap (hidden when minimized)
    logControls: { // controls for log
        autoscrollCheckboxValue: Ref<boolean>, // element id of autoscroll checkbox
        disableCheckboxValue: Ref<boolean>, // element id of log disable checkbox
        minimizeToggleElementId: string, // element id of log minimize/unminimize toggle
    },
    windowManager: { // console window manager
        desktopElementId: string,
        taskbarElementId: string,
    },
    replayControls: { // replay controls
        recordButtonValue: replayValueType, // element id of record button
        replayButtonValue: replayValueType, // element id of replay button
        stopButtonValue: replayValueType // element id of stop button
        backwardButtonValue: replayValueType, // element id of backward button
        forwardButtonValue: replayValueType, // element id of forward button
        seekBarValue: replayValueType, // element id of seek bar
        intervalValue: replayValueType, // element id of interval input
    },
    replayStatusInfo: {
        text: string,
        status: string,
        disabled: boolean
    }
}

type FilterMode = 'node-search' | 'filter';
type SuggestionSelectionAction = 'up' | 'down' | 'clear';

interface Event {
    lines: string[],
    source: string
}

interface PlaylistItem {
    nodes: string[],
    at: number
}

const staticDefault = {borderWidth: 1}
const dynamicDefault = {borderWidth: 4}

/**
 * map UI controller.
 */
export class MapUi {
    private readonly _mapElement: HTMLElement;
    protected _datasource: DataSource;

    private _filterInputValue: Ref<string>;
    protected allLoadingInstance: LoadingInstance;

    private _logPanel: HTMLElement;
    private _logView: HTMLElement;
    private _logWrap: HTMLElement;
    private _logBody: HTMLElement;
    private _logAutoscroll: Ref<boolean>;
    private _logDisable: Ref<boolean>;
    private _logToggle: HTMLElement;

    private _suggestions: HTMLElement;
    private allService: Ref<string[]>;

    private _replayButton: replayValueType;
    private _recordButton: replayValueType;
    private _forwardButton: replayValueType;
    private _backwardButton: replayValueType;
    private _stopButton: replayValueType;
    private _replaySeekBar: replayValueType;
    private _interval: replayValueType;

    public replayStatusInfo: {
        text: string,
        status: string,
        disabled: boolean
    };

    private _clickTimer: number | null;

    private _nodes: NodesType;
    private _edges: EdgesType;
    private _graph: Network;

    private detailsDialogVisible: Ref<boolean>
    private vertexDetails: Ref<Details[]>

    /** list of log elements to be rendered to log body */
    private _logQueue: HTMLElement[];

    /** set of vertex ids scheduled for flashing */
    private readonly _flashQueue: Set<string>;
    /** set of vertex ids scheduled for un-flash */
    private _flashingNodes: Set<string>;

    // vis
    private _visSetQueue: Set<string>;
    private readonly _flashVisQueue: Set<string>;
    private _flashingVisNodes: Set<string>;

    private _logPrinter: number;
    private _flasher: number;
    private _flasherVis: { [key: string]: number };

    private readonly _macMapping: { [mac: string]: string };
    private readonly _macContainerIDMapping: { [mac: string]: string };

    private _filterMode: FilterMode;

    /** set of vertex ids for nodes/nets currently being highlighted by search  */
    private _searchHighlightNodes: Set<string>;

    private _lastSearchTerm: string;

    /** window manager for consoles.  */
    private _windowManager: WindowManager;

    /** completion provider for bpf expressions. */
    private _bpfCompletion: Completion;

    /** current (or last selected, if none is selected now) vertex. */
    private _curretNode: Vertex;

    /** current suggestion item selection. */
    private _suggestionsSelection: number;

    /**
     * ignore next keyup event. (set to true when event is already handled in
     * keydown.)
     */
    private _ignoreKeyUp: boolean;

    private _logMinimized: boolean;
    private _settingMinimized: boolean;

    private _events: Event[];
    private _playlist: PlaylistItem[];
    private _replayStatus: 'stopped' | 'playing' | 'paused';
    private _recording: boolean;
    private _replayTask: number;
    private _replayPos: number;
    private _seeking: boolean;

    private _firstIntervalStartTime: number
    private _intervalDefault: number
    private _flashVisStyleMapping: { [key: string]: { [key: string]: number | NodeOptions } }
    private _otherConfiguration: {};

    /**
     * Build a new map UI controller.
     *
     * @param config element bindings.
     * @param otherConfiguration
     */
    constructor(config: MapUiConfiguration, otherConfiguration = {}) {
        this._otherConfiguration = otherConfiguration;
        this.allService = config.allService
        this._datasource = config.datasource;
        this.detailsDialogVisible = config.detailsDialogVisible as Ref<boolean>
        this.vertexDetails = config.details
        this._filterInputValue = config.filterInputValue;
        // this._searchInput = document.getElementById(config.searchInputElementId) as HTMLInputElement;
        this.allLoadingInstance = allLoading()
        this._mapElement = document.getElementById(config.mapElementId) as HTMLElement;

        this._logPanel = document.getElementById(config.logPanelElementId) as HTMLElement;
        this._logView = document.getElementById(config.logViewportElementId) as HTMLElement;
        this._logWrap = document.getElementById(config.logWrapElementId) as HTMLElement;
        this._logBody = document.getElementById(config.logBodyElementId) as HTMLElement;
        this._logAutoscroll = config.logControls.autoscrollCheckboxValue;
        this._logDisable = config.logControls.disableCheckboxValue;

        this._logToggle = document.getElementById(config.logControls.minimizeToggleElementId) as HTMLElement;

        this._suggestions = document.getElementById(config.suggestionsElementId) as HTMLElement;

        this._replayButton = config.replayControls.replayButtonValue
        this._recordButton = config.replayControls.recordButtonValue;
        this._stopButton = config.replayControls.stopButtonValue;
        this._forwardButton = config.replayControls.forwardButtonValue;
        this._backwardButton = config.replayControls.backwardButtonValue;
        this._replaySeekBar = config.replayControls.seekBarValue;
        this._interval = config.replayControls.intervalValue;

        this.replayStatusInfo = config.replayStatusInfo
        this._clickTimer = null


        this._intervalDefault = 500;
        this._flashVisStyleMapping = {};

        this._logMinimized = true;
        this._settingMinimized = true;

        this._replayStatus = 'stopped';
        this._events = [];
        this._recording = false;
        this._seeking = false;
        this._playlist = [];

        this._suggestionsSelection = -1;

        this._logQueue = [];
        this._logPrinter = this._flasher = 0

        this._flashQueue = new Set<string>();
        this._flashingNodes = new Set<string>();
        this._flashVisQueue = new Set<string>();
        this._flashingVisNodes = new Set<string>();
        this._flasherVis = {};
        this._visSetQueue = new Set<string>();

        this._searchHighlightNodes = new Set<string>();

        this._macMapping = {};
        this._macContainerIDMapping = {};

        this._filterMode = 'filter';
        this._lastSearchTerm = '';

        this._bpfCompletion = new Completion(bpfCompletionTree);

        this._windowManager = new WindowManager(config.windowManager.desktopElementId, config.windowManager.taskbarElementId);

        this._bpfCompletion = new Completion(bpfCompletionTree);

        this._logToggle.onclick = () => {
            if (this._logMinimized) {
                this._logWrap.classList.remove('minimized');
            } else {
                this._logWrap.classList.add('minimized');
            }

            this._logMinimized = !this._logMinimized;
        };

        this._windowManager.on('taskbarchanges', (shown: boolean) => {
            if (shown) {
                this._logPanel.classList.add('bump');
            } else {
                this._logPanel.classList.remove('bump');
            }
        });

        this._datasource.on('dead', (error) => {
            let restart = window.confirm('It seems like the backend for seedemu-client has crashed. You should refresh this page to get the connection to the backend re-established.\n\nRefreshing will close all console windows and redraw the map. Use "Ok" to refresh or "cancel" to stay on this page.');
            if (restart) {
                window.location.reload();
            }
        });

        this._datasource.on('packet', (data) => {
            // bad data?
            if (!data.source || !data.data) {
                return;
            }

            // replaying?
            if (this._replayStatus !== 'stopped') {
                return;
            }

            let flashed = new Set<string>();

            // find network with matching mac address and flash the network too.
            // networks objects are never the source, as network cannot run
            // tcpdump on its own.
            Object.keys(this._macMapping).forEach(mac => {
                if (data.data.includes(mac) && !flashed.has(mac)) {
                    flashed.add(mac);
                    let nodeId = this._macMapping[mac] as string;

                    if (this._nodes.get(nodeId) === null) {
                        return;
                    }
                    this._flashQueue.add(nodeId);
                }
            });

            // at least one mac address matching a net is found, flash the node.
            // note: when no matching net is found, the "packet" may not be a
            // packet, but output from tcpdump.
            if (flashed.size > 0) {
                const nodeId = data.source;
                if (this._visSetQueue.has(nodeId)) {
                    this._flashVisQueue.add(nodeId);
                } else {
                    this._flashQueue.add(nodeId);
                }
            }

            let now = new Date();
            let lines: string[] = data.data.split('\r\n').filter((line: string) => line !== '');

            if (lines.length > 0 && this._recording) {
                this._events.push({lines: lines, source: data.source});
            }

            // tcpdump output: "listening on xxx", meaning tcpdump is running
            // and the last expressions does not contain error.
            // if (data.data.includes('listening')) {
            //     this._filterInput.classList.remove('error');
            //     // this._filterWrap.classList.remove('error');
            // }

            // tcpdump output: "error", meaning tcpdump don't like the last
            // expression
            // if (data.data.includes('error')) {
            //     this._filterInput.classList.add('error');
            //     // this._filterWrap.classList.add('error');
            // }

            if (this._logDisable.value) {
                return;
            }

            let node = this._nodes.get(data.source as string) as FullItem<Vertex, "id">;
            if (node === null) {
                return;
            }

            let timeString = `${now.getHours()}:${now.getMinutes()}:${now.getSeconds()}.${now.getMilliseconds()}`;

            let tr = document.createElement('tr');

            let td0 = document.createElement('td');
            let td1 = document.createElement('td');
            let td2 = document.createElement('td');

            td0.innerText = timeString;

            let a = document.createElement('a');

            a.href = '#';
            a.innerText = node.label;
            a.onclick = async () => {
                await this._focusNode(node.id);
            };

            td1.appendChild(a);

            td2.innerText = data.data;

            tr.appendChild(td0);
            tr.appendChild(td1);
            tr.appendChild(td2);

            this._logQueue.push(tr);
        });

        this._datasource.on('vis', (data) => {
            // bad data?
            if (!data.source || !data.data) {
                return;
            }
            if (!this._nodes) {
                return;
            }
            const _data = JSON.parse(data.data);
            const nodeId = data.source;
            if (nodeId in this._flasherVis) {
                window.clearInterval(this._flasherVis[nodeId]);
            }

            if (_data.action === 'flashOnce') {
                this._flashVisNodes(
                    nodeId, _data.interval, _data.static, _data.dynamic, _data.action
                )
            } else {
                const currentTime = new Date().getTime();
                const offset = currentTime - this._firstIntervalStartTime;
                const adjustedDelay = this._intervalDefault - (offset % this._intervalDefault);
                window.setTimeout(() => {
                    this._flasherVis[nodeId] = window.setInterval(() => {
                        this._flashVisNodes(
                            nodeId, _data.interval, _data.static, _data.dynamic, _data.action
                        )
                    }, this._intervalDefault);
                }, adjustedDelay)
            }
        });
    }

    public setDragFixed = (val: boolean) => {
        this._graph.setOptions({physics: !val});
    }

    public recordStartStop() {
        if (this._replayStatus !== 'stopped') {
            return;
        }

        if (this._recording) {
            this._recording = false;
            this.replayStatusInfo.text = 'Replay stopped.';
            this._updateReplayControls();
        } else {
            this._events = [];
            this._recording = true;
            this.replayStatusInfo.text = 'Recording events...';
            this._updateReplayControls();
        }
    }

    public replayPlayPause() {
        if (this._recording) {
            return;
        }

        if (this._replayStatus === 'stopped') {
            this._replayPos = 0;
            this.replayStatusInfo.text = 'Replay stopped.';
            this._replayStatus = this.replayStatusInfo.status = 'playing';
            this._playlist = this._buildPlayList();
            this._doReplay();
            this._updateReplayControls();
        } else if (this._replayStatus === 'playing') {
            this._replayStatus = this.replayStatusInfo.status = 'paused';
            this._updateReplayControls();
        } else if (this._replayStatus === 'paused') {
            this._replayStatus = this.replayStatusInfo.status = 'playing';
            this._updateReplayControls();
        }
    }

    public replayStop() {
        if (this._replayStatus === 'stopped') {
            return;
        }

        this._replayStatus = this.replayStatusInfo.status = 'stopped';
        window.clearTimeout(this._replayTask);

        // un-flash nodes.
        let unflashRequest = Array.from(this._flashingNodes).map(nodeId => {
            return {
                id: nodeId, ...staticDefault
            }
        });
        this._nodes.update(unflashRequest);
        this._flashingNodes.clear();
        this._flashingVisNodes.clear();
        this._updateReplayControls();
        this.replayStatusInfo.text = 'Replay stopped.';
    }

    public replaySeek(offset: number, absolute: boolean = false) {
        if (this._replayStatus === 'stopped') {
            return;
        }

        this._replayStatus = this.replayStatusInfo.status = 'paused';
        this._updateReplayControls();

        if (absolute) {
            this._replayPos = offset;
        } else {
            this._replayPos += offset;
        }

        this._doReplay(true);
    }

    public replaySeekMousedown = () => {
        this._seeking = true;
    };

    public replaySeekMouseup = () => {
        this._seeking = false;
    };

    private _updateReplayControls() {
        if (this._replayStatus === 'playing' || this._replayStatus === 'paused') {
            this._replayButton.disabled = false;
            this._recordButton.disabled = true;
            this._stopButton.disabled = false;
            this._forwardButton.disabled = false;
            this._backwardButton.disabled = false;
            this._replaySeekBar.disabled = false;
            this._interval.disabled = this._replayStatus === 'playing';

            this._replaySeekBar.max = (this._playlist.length - 1).toString();
            // this._replayButton.innerHTML = this._replayStatus === 'playing' ? '<i class="bi bi-pause"></i>' : '<i class="bi bi-play-fill"></i>';
            // this._recordButton.innerHTML = '<i class="bi bi-record-fill"></i>';
        }

        if (this._replayStatus === 'stopped') {
            this._replayButton.disabled = this._recording;
            this._recordButton.disabled = false;
            this._stopButton.disabled = true;
            this._forwardButton.disabled = true;
            this._backwardButton.disabled = true;
            this._replaySeekBar.disabled = true;
            this._interval.disabled = false;

            // this._replayButton.innerHTML = '<i class="bi bi-play-fill"></i>';
            // this._recordButton.innerHTML = this._recording ? '<i class="bi bi-stop-fill"></i>' : '<i class="bi bi-record-fill"></i>';
        }
    }

    private _buildPlayList(): PlaylistItem[] {
        let refDate = new Date();

        let playlist: PlaylistItem[] = [];

        this._events.forEach(e => {
            e.lines.forEach(line => {
                let time = line.split(' ')[0] as string;
                let [h, m, _s] = time.split(':');

                if (!h || !m || !_s) {
                    return;
                }

                let [s, ms] = _s.split('.');

                let nodes: string[] = [e.source];
                let added: Set<string> = new Set();
                let date = new Date(refDate.getFullYear(), refDate.getMonth(), refDate.getDate(), parseInt(h), parseInt(m), parseInt(s), parseInt(ms));

                Object.keys(this._macMapping).forEach(mac => {
                    if (line.includes(mac) && !added.has(mac)) {
                        added.add(mac);

                        let nodeId = this._macMapping[mac];

                        if (this._nodes.get(nodeId) === null) {
                            return;
                        }

                        nodes.push(nodeId);
                    }
                });

                playlist.push({nodes: nodes, at: date.valueOf()});
            });

        });

        return playlist.sort((a, b) => a.at - b.at);
    }

    getter = () => {
        return {
            _datasource: this._datasource,
            _nodes: this._nodes,
            _edges: this._edges,
            _graph: this._graph,
        }
    }

    /**
     * get a random color.
     *
     * @returns hsl color string.
     */
    private _randomColor(): string {
        return `hsl(${Math.random() * 360}, 100%, 75%)`;
    }

    /**
     * Find all edge ids that meet the from condition
     * **/
    private _findEdgeIds(fromNode) {
        const allEdges = this._edges.get();
        const edgeIds = new Array<string>();
        allEdges.forEach(edge => {
            // if (edge.from === fromNode && (this._flashingNodes.has(edge.to) || this._flashingVisNodes.has(edge.to))) {
            if (edge.from === fromNode) {
                edgeIds.push(edge.id);
            }
        });
        return edgeIds ? edgeIds : null;
    }

    private _findEdgeId2(fromNode, toNode) {
        const allEdges = this._edges.get();
        let edgeId = null;
        allEdges.forEach(edge => {
            if (edge.from === fromNode && edge.to === toNode) {
                edgeId = edge.id;
            }
        });
        return edgeId;
    }

    /**
     * update highlighed nodes on the map. will auto un-highligh previously
     * highlighted nodes.
     *
     * @param highlights set of vertex ids to highlight.
     */
    private _updateSearchHighlights(highlights: Set<string>) {
        var newHighlights = new Set<string>();
        var unHighlighted = new Set<string>();

        highlights.forEach(n => {
            if (!this._searchHighlightNodes.has(n)) {
                newHighlights.add(n);
            }
        });

        this._searchHighlightNodes.forEach(n => {
            if (!highlights.has(n)) {
                unHighlighted.add(n);
            }
        });

        unHighlighted.forEach(n => {
            this._searchHighlightNodes.delete(n);
        });

        newHighlights.forEach(n => {
            this._searchHighlightNodes.add(n);
        });

        var updateRequest = [];

        newHighlights.forEach(n => {
            updateRequest.push({
                id: n, ...dynamicDefault
            });
        });

        unHighlighted.forEach(n => {
            updateRequest.push({
                id: n, ...staticDefault
            });
        });

        this._nodes.update(updateRequest);
    }

    /**
     * flash all nodes in the flash queue and schedule un-flash.
     */

    private _flashVisNodes(
        nodeId: string,
        interval: number = 300,
        _static: {} = staticDefault,
        dynamic: {} = dynamicDefault,
        action: string
    ) {
        // during replay, do not flash nodes - they are controlled by the replayer.
        if (this._replayStatus !== 'stopped') {
            return;
        }

        let shape: string;
        if (this._nodes.get(nodeId)?.type === 'node') {
            const nodeInfo = this._datasource.getNodeInfoById(nodeId);
            shape = ['Router', 'BorderRouter'].includes(nodeInfo.meta.emulatorInfo.role) ? 'dot' : 'hexagon';
        }

        if (Object.keys(_static).length === 0) {
            _static = staticDefault
        }
        if (!_static.hasOwnProperty('shape')) {
            _static['shape'] = shape
        }
        if (Object.keys(dynamic).length === 0) {
            dynamic = dynamicDefault
        }

        switch (action) {
            case 'flashOnce':
            case 'flash':
                return this._flashVisNodesFlash(nodeId, _static, dynamic, interval);
            case 'highlight':
                return this._flashVisNodesHighlight(nodeId, _static);
            default:
                break
        }

        if (this._flashingVisNodes.size != 0 && !this._flashingVisNodes.has(nodeId)) {
            // some nodes still flashing; wait for next time
            return;
        }

        if (this._filterMode == 'node-search') {
            // in node search mode, don't flash.
            this._flashingVisNodes.clear();
            return;
        }

        this._visSetQueue.add(nodeId)
        let updateEdgeIds = new Set<string>();
        this._findEdgeIds(nodeId).forEach(edgeId => updateEdgeIds.add(edgeId));
        this._nodes.update({
            id: nodeId, ..._static
        });
        this._flashVisStyleMapping[nodeId] = {
            interval,
            'static': _static as NodeOptions,
            'dynamic': dynamic as NodeOptions,
        }

        if (interval > 0) {
            // schedule un-flash
            window.setTimeout(() => {
                this._flashingVisNodes = new Set(this._flashVisQueue);
                this._flashVisQueue.delete(nodeId);
                if (!this._flashingVisNodes.has(nodeId)) {
                    return
                }

                this._nodes.update({
                    id: nodeId, ...dynamic
                });
            }, interval);
        }
    }

    private _flashVisNodesFlash(nodeId: string, _static: {}, dynamic: {}, interval: number) {
        this._nodes.update({
            id: nodeId, ..._static
        });
        window.setTimeout(() => {
            this._nodes.update({
                id: nodeId, ...dynamic
            });
        }, interval);
    }

    private _flashVisNodesHighlight(nodeId: string, highLight: {}) {
        this._nodes.update({
            id: nodeId, ...highLight
        });
    }

    private async _focusNode(id: string) {
        this._graph.focus(id, {animation: true});
        this._graph.selectNodes([id]);
        this._updateInfoPlateWith(id);
    }

    /**
     * find net or nodes search term.
     *
     * @param term search term.
     * @returns list of stuffs matching the term.
     */
    private _findNodes(term: string): Vertex[] {
        var hits: Vertex[] = [];

        this._nodes.forEach(node => {
            var targetString = '';

            if (node.type == 'node') {
                let nodeObj = (node.object as EmulatorNode);
                let nodeInfo = nodeObj.meta.emulatorInfo;

                targetString = `${nodeObj.Id} ${nodeInfo.role} as${nodeInfo.asn} ${nodeInfo.name} ${nodeInfo.displayname ?? ''} ${nodeInfo.description ?? ''}`;

                nodeInfo.nets.forEach(net => {
                    targetString += `${net.name} ${net.address} `;
                });
            }

            if (node.type == 'network') {
                let net = (node.object as EmulatorNetwork);
                let netInfo = net.meta.emulatorInfo;

                targetString = `${net.Id} as${netInfo.scope} ${netInfo.name} ${netInfo.prefix} ${netInfo.displayname ?? ''} ${netInfo.description ?? ''}`;
            }

            if (term != '' && targetString.toLowerCase().includes(term.toLowerCase())) {
                hits.push(node);
            }
        });

        return hits;
    }

    /**
     * move filter/search suggestions selection.
     *
     * @param selection move direction.
     */
    private _moveSuggestionSelection(selection: SuggestionSelectionAction) {
        let children = this._suggestions.children;

        if (children.length == 0) {
            return;
        }

        if (selection == 'clear') {
            if (children.length == 0) {
                return;
            }

            this._suggestionsSelection = -1;
            Array.from(children).forEach(child => {
                child.classList.remove('active');
            });

            return;
        }

        if (selection == 'up') {
            if (this._suggestionsSelection <= 0) {
                return;
            }

            this._suggestionsSelection--;

            children[this._suggestionsSelection + 1].classList.remove('active');
        }

        if (selection == 'down') {
            if (this._suggestionsSelection == children.length - 1) {
                return;
            }

            this._suggestions.focus();

            this._suggestionsSelection++;

            if (this._suggestionsSelection > 0) {
                children[this._suggestionsSelection - 1].classList.remove('active');
            }
        }

        let current = children[this._suggestionsSelection] as Element;
        current.classList.add('active');

        let boxRect = this._suggestions.getBoundingClientRect();
        let itemRect = current.getBoundingClientRect();

        let topOffset = itemRect.top - boxRect.top;
        let bottomOffset = itemRect.bottom - boxRect.bottom;

        if (topOffset < 0) {
            this._suggestions.scrollBy({top: topOffset - 10, behavior: 'smooth'});
        }

        if (bottomOffset > 0) {
            this._suggestions.scrollBy({top: bottomOffset + 10, behavior: 'smooth'});
        }
    }

    /**
     * update filter/search suggestions.
     *
     * @param term current search/filter term.
     */
    public updateFilterSuggestions(term: string) {
        this._suggestions.innerText = '';

        if (this._filterMode == 'filter') {
            this._bpfCompletion.getCompletion(term).forEach(comp => {

                let item = document.createElement('div');
                item.className = 'suggestion';

                var title = comp.fulltext;
                var fillText = comp.partialword;

                if (this._curretNode) {
                    if (this._curretNode.type == 'network') {
                        let prefix = (this._curretNode.object as EmulatorNetwork).meta.emulatorInfo.prefix;

                        title = title.replace('<net>', prefix);
                        fillText = fillText.replace('<net>', prefix);
                    }

                    if (this._curretNode.type == 'node') {
                        let addresses = (this._curretNode.object as EmulatorNode).meta.emulatorInfo.nets.map(net => net.address.split('/')[0]);
                        let addressesExpr = addresses.join(' or ');

                        if (addresses.length > 1) {
                            addressesExpr = `(${addressesExpr})`;
                        }

                        title = title.replace('<host>', addressesExpr);
                        fillText = fillText.replace('<host>', addressesExpr);
                    }
                }

                let name = document.createElement('span');
                name.className = 'name';
                name.innerText = title;

                let details = document.createElement('span');
                details.className = 'details';
                details.innerText = comp.description;

                item.appendChild(name);
                item.appendChild(details);
                item.onclick = () => {
                    this._filterInputValue.value += `${fillText} `;
                    this._moveSuggestionSelection('clear');
                    this.updateFilterSuggestions(this._filterInputValue.value);
                };

                this._suggestions.appendChild(item);
            });
        }

        if (this._filterMode == 'node-search') {
            let vertices = this._findNodes(term);

            if (term != '') {
                let defaultItem = document.createElement('div');
                defaultItem.className = 'suggestion';

                let defaultName = document.createElement('span');
                defaultName.className = 'name';
                defaultName.innerText = term;

                let defailtDetails = document.createElement('span');
                defailtDetails.className = 'details';
                defailtDetails.innerText = 'Press enter to show all matches on the map...';

                defaultItem.onclick = () => {
                    this._moveSuggestionSelection('clear');
                    this._filterUpdateHandler(undefined, true);
                };

                defaultItem.appendChild(defaultName);
                defaultItem.appendChild(defailtDetails);

                this._suggestions.appendChild(defaultItem);
            }

            vertices.forEach(vertex => {
                var itemName = vertex.label;
                var itemDetails = '';

                if (vertex.type == 'node') {
                    let node = vertex.object as EmulatorNode;

                    itemDetails = node.meta.emulatorInfo.nets.map(net => net.address).join(', ');
                    itemName = `${node.meta.emulatorInfo.role}: ${itemName}`;
                }

                if (vertex.type == 'network') {
                    let net = vertex.object as EmulatorNetwork;

                    itemDetails = net.meta.emulatorInfo.prefix;
                    itemName = `${net.meta.emulatorInfo.type == 'global' ? 'Exchange' : 'Network'}: ${itemName}`;
                }

                let item = document.createElement('div');
                item.className = 'suggestion';

                let name = document.createElement('span');
                name.className = 'name';
                name.innerText = itemName;

                let details = document.createElement('span');
                details.className = 'details';
                details.innerText = itemDetails;

                item.appendChild(name);
                item.appendChild(details);

                item.onclick = () => {
                    this._focusNode(vertex.id);
                    let set = new Set<string>();
                    set.add(vertex.id);
                    this._updateSearchHighlights(set);
                    this._suggestions.innerText = '';
                    this._moveSuggestionSelection('clear');
                };

                this._suggestions.appendChild(item);
            });
        }
    }

    /**
     * commit a filter search.
     *
     * @param event if triggerd by keydown/keyup event, the event.
     * @param forced if not triggerd by keydown/keyup event, set to true.
     */
    private async _filterUpdateHandler(event: KeyboardEvent | undefined, forced: boolean = false) {
        let term = this._filterInputValue.value;

        if (((!event || event.key != 'Enter') && !forced)) {
            this._moveSuggestionSelection('clear');
            this._suggestions.innerText = '';
            this.updateFilterSuggestions(term);

            return;
        }

        this._suggestions.innerText = '';

        if (this._filterMode == 'filter') {
            this._filterInputValue.value = await this._datasource.setSniffFilter(term);
        }

        if (this._filterMode == 'node-search') {
            var hits = new Set<string>();
            this._lastSearchTerm = term;

            this._findNodes(term).forEach(node => hits.add(node.id));

            this._updateSearchHighlights(hits);
        }
    }

    /**
     * create an infoplate label/text field.
     *
     * @param label label for the pair.
     * @param text text for the pair.
     * @returns div element of the pair.
     */
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

    public async setFilterMode(mode: FilterMode) {
        if (mode == this._filterMode) {
            return;
        }

        this._filterMode = mode;

        this._suggestions.innerText = '';
        this._moveSuggestionSelection('clear');

        if (mode == 'filter') {
            this._updateSearchHighlights(new Set<string>());
        }

        if (mode == 'node-search') {
            await this._filterUpdateHandler(undefined, true);
        }
    }

    public createWindow(nodeId: string, title: string, queryData: IframeQueryData = {cmd: ''}) {
        this._windowManager.createWindow(nodeId.substr(0, 12), title, queryData, true);
    }

    /**
     * update infoplate with node.
     *
     * @param nodeId node id for any vertex (can be node or net).
     */
    private async _updateInfoPlateWith(nodeId: string): Promise<Details[]> {
        let vertex = this._nodes.get(nodeId) as Vertex;
        let vertexDetails: Details[] = []

        this._curretNode = vertex;

        let infoPlate = document.createElement('div');

        let title = document.createElement('div');
        title.className = 'title';
        infoPlate.appendChild(title);

        if (vertex.type == 'network') {
            let detail: Details = {title: '', data: {}}
            let net = vertex.object as EmulatorNetwork;
            detail.title = `${net.meta.emulatorInfo.type == 'global' ? 'Exchange' : 'Network'}: ${vertex.label}`;

            if (net.meta.emulatorInfo.description) {
                detail.data.Des = net.meta.emulatorInfo.description
            }
            detail.data.ID = net.Id.substr(0, 12)
            detail.data.Name = net.meta.emulatorInfo.name
            detail.data.Scope = net.meta.emulatorInfo.scope
            detail.data.Type = net.meta.emulatorInfo.type
            detail.data.Prefix = net.meta.emulatorInfo.prefix

            vertexDetails.push(detail)
        }

        if (vertex.type == 'node') {
            let detail1: Details = {title: '', data: {}}
            let detail2: Details = {title: '', data: {}}
            let detail3: Details = {title: '', data: {}}
            let detail4: Details = {title: '', data: {}}
            let node = vertex.object as EmulatorNode;
            detail1.title = `${['Router', 'BorderRouter'].includes(node.meta.emulatorInfo.role) ? 'Router' : 'Host'}: ${vertex.label}`;

            if (node.meta.emulatorInfo.description) {
                detail1.data.Des = node.meta.emulatorInfo.description
            }
            detail1.data.ID = node.Id.substr(0, 12)
            detail1.data.ASN = node.meta.emulatorInfo.asn.toString()
            detail1.data.Name = node.meta.emulatorInfo.name
            detail1.data.Role = node.meta.emulatorInfo.role

            detail2.title = 'IP addresses';
            node.meta.emulatorInfo.nets.forEach(net => {
                detail2.data[net.name] = net.address
            });

            if (vertex.custom !== 'custom' && CONSOLE !== 'false') {
                if (['Router', 'Route Server', 'BorderRouter'].includes(node.meta.emulatorInfo.role)) {
                    let peers = await this._datasource.getBgpPeers(node.Id);
                    detail3.title = 'BGP sessions';
                    peers.forEach(peer => {
                        const peerStatus = peer.protocolState != 'down' ? peer.bgpState : 'Disabled'
                        const peerAction = peer.protocolState != 'down' ? 'Disable' : 'Enable'
                        // detail3.data[peer.name] = [peerStatus, peerAction]

                        let _peerAction = document.createElement('a');
                        _peerAction.href = '#';
                        _peerAction.classList.add(CLICK_CLASS.PEER_ACTION_CLASS);
                        _peerAction.setAttribute("params", JSON.stringify({
                            node: node.Id,
                            peer: peer.name,
                            up: peer.protocolState == 'down',
                        }))
                        _peerAction.innerText = peer.protocolState != 'down' ? 'Disable' : 'Enable';
                        detail3.data[peer.name] = [peerStatus, _peerAction.outerHTML]
                    });
                }

                let actions = document.createElement('div');
                actions.classList.add('section');

                let actionTitle = document.createElement('div');
                actionTitle.className = 'title';
                detail4.title = 'Actions';
                actions.appendChild(actionTitle);

                let consoleLink = document.createElement('a');
                consoleLink.href = '#';
                consoleLink.innerText = 'Launch console';
                consoleLink.classList.add(CLICK_CLASS.CONSOLE_CLASS);
                consoleLink.setAttribute("params", JSON.stringify({
                    nodeId: node.Id.substr(0, 12),
                    label: vertex.label,
                }))
                detail4.data["Launch console"] = consoleLink.outerHTML

                let netToggle = document.createElement('a');
                let netState = await this._datasource.getNetworkStatus(node.Id);

                netToggle.href = '#';
                netToggle.innerText = netState ? 'Disconnect' : 'Re-connect'
                netToggle.classList.add(CLICK_CLASS.NET_TOGGLE_CLASS);
                netToggle.setAttribute("params", JSON.stringify({
                    nodeId: node.Id,
                    nodeRole: node.meta.emulatorInfo.role,
                    netState,
                }))
                detail4.data["netState"] = netToggle.outerHTML

                let reloadLink = document.createElement('a');

                reloadLink.href = '#';
                reloadLink.innerText = 'Refresh';
                reloadLink.classList.add(CLICK_CLASS.RELOAD_CLASS);
                reloadLink.setAttribute("params", JSON.stringify({
                    nodeId: node.Id,
                }))
                detail4.data["Refresh"] = reloadLink.outerHTML
            }

            vertexDetails.push(detail1)
            vertexDetails.push(detail2)
            vertexDetails.push(detail3)
            vertexDetails.push(detail4)
        }

        return vertexDetails
    }

    private _expandNode(nodeId: string) {
        const children = this._nodes.get({
            filter: item => item.object.meta.relation.parent.size === 1 && [...item.object.meta.relation.parent][0] === nodeId
        });
        if (children.length === 0) {
            return
        }

        let updates = children.map(child => ({
            id: child.id,
            hidden: false,
        } as any));
        updates.push({id: nodeId, collapsed: false, borderWidth: 1})
        this._nodes.update(updates);

        children.forEach(child => {
            if (!child.collapsed) {
                this._expandNode(child.id);
            }
        });
    }

    private _collapseNode(nodeId: string) {
        const descendants = this._getAllDescendants(nodeId);
        if (descendants.length === 0) {
            return
        }

        let updates = descendants.map(desc => ({
            id: desc.id,
            hidden: true,
        } as any));
        updates.push({id: nodeId, collapsed: true, borderWidth: 3})
        this._nodes.update(updates);
    }

    private _getAllDescendants(nodeId: string) {
        let descendants = [];
        const stack = [nodeId];

        while (stack.length > 0) {
            const currentId = stack.pop();
            const children = this._nodes.get({
                filter: item => item.object.meta.relation.parent.size === 1 && [...item.object.meta.relation.parent][0] === currentId
            });

            children.forEach(child => {
                descendants.push(child);
                stack.push(child.id);
            });
        }

        let other = new Set<string>();
        this._nodes.get().forEach(item => {
            if (!descendants.find(d => d.id === item.id)) {
                item.object.meta.relation.parent.forEach(i => other.add(i))
            }
        })

        descendants = descendants.filter(item => !other.has(item.id))

        return descendants;
    }

    /**
     * map mac addresses to networks.
     */
    private _mapMacAddresses() {
        this._nodes.forEach(vertex => {
            if (vertex.type != 'node') {
                return;
            }

            let node = vertex.object as EmulatorNode;

            Object.keys(node.NetworkSettings.Networks).forEach(key => {
                let net = node.NetworkSettings.Networks[key];
                this._macMapping[net.MacAddress] = net.NetworkID;
                this._macContainerIDMapping[net.MacAddress] = node.Id;
            });
        });
    }

    private _doReplay(once: boolean = false) {
        // not playing.
        if (this._replayStatus === 'stopped') {
            return;
        }

        if (!once) {
            this._replayTask = window.setTimeout(() => this._doReplay(), this._interval.value)
        }

        this.replayStatusInfo.text = `${this._replayStatus === 'paused' ? 'Paused' : 'Playing'}: ${this._replayPos}/${this._playlist.length} event(s) left.`;

        if (!this._seeking) {
            this._replaySeekBar.value = this._replayPos;
        }

        // reached the end.
        if (this._replayPos >= this._playlist.length) {
            this._replayStatus = this.replayStatusInfo.status = 'paused';
            this.replayStatusInfo.text = 'End of record.';
            this._replaySeekBar.value = 0;
            this._replayPos = 0;
            this._updateReplayControls();
            return;
        }

        // un-flash nodes.
        let unFlashRequest = Array.from(this._flashingNodes).map(nodeId => {
            let style: {};
            if (this._flashVisStyleMapping.hasOwnProperty(nodeId)) {
                style = this._flashVisStyleMapping[nodeId]?.static as {};
            } else {
                style = staticDefault;
            }
            return {
                id: nodeId, ...style
            }
        });
        this._nodes.update(unFlashRequest);
        this._flashingNodes.clear();
        this._flashingVisNodes.clear();

        // flash nodes from this event.
        let current = this._playlist[this._replayPos];
        current?.nodes.forEach(node => this._flashingNodes.add(node));
        let flashRequest = Array.from(this._flashingNodes).map(nodeId => {
            let style: {};
            if (this._flashVisStyleMapping.hasOwnProperty(nodeId)) {
                style = this._flashVisStyleMapping[nodeId]!.dynamic as NodeOptions;
            } else {
                style = dynamicDefault;
            }
            return {
                id: nodeId, ...style
            }
        });
        this._nodes.update(flashRequest);

        if (this._replayStatus === 'playing') {
            ++this._replayPos;
        }
    }

    private _flashNodes() {
        // during replay, do not flash nodes - they are controlled by the replayer.
        if (this._replayStatus !== 'stopped') {
            return;
        }

        if (this._flashingNodes.size != 0) {
            // some nodes still flashing; wait for next time
            return;
        }

        this._flashingNodes = new Set(this._flashQueue);
        this._flashQueue.clear();

        if (this._filterMode == 'node-search') {
            // in node search mode, don't flash.
            this._flashingNodes.clear();
            return;
        }

        let updateRequest = Array.from(this._flashingNodes).map(nodeId => {
            return {
                id: nodeId, ...dynamicDefault
            }
        });

        this._nodes.update(updateRequest);

        // schedule un-flash
        window.setTimeout(() => {
            let updateRequest = Array.from(this._flashingNodes).map(nodeId => {
                return {
                    id: nodeId, ...staticDefault
                }
            });
            this._nodes.update(updateRequest);
            this._flashingNodes.clear();
        }, 300);
    }

    /**
     * connect datasource, start mapping, and start the log/flash workers.
     */
    async start() {
        await this._datasource.connect();
        this.allService.value = [...this._datasource.services]
        this.redraw();
        this._mapMacAddresses();

        this._filterInputValue.value = await this._datasource.getSniffFilter();

        this._logPrinter = window.setInterval(() => {
            let scroll = false;

            while (this._logQueue.length > 0) {
                scroll = true;
                this._logBody.appendChild(this._logQueue.shift()!);
            }

            if (scroll && this._logAutoscroll.value && !this._logDisable.value) {
                this._logView.scrollTop = this._logView.scrollHeight;
            }
        }, this._intervalDefault);

        this._flasher = window.setInterval(() => {
            this._flashNodes();
        }, this._intervalDefault);
        this._firstIntervalStartTime = new Date().getTime();
    }

    /**
     * disconnect datasource and stop log/flash worker.
     */
    stop() {
        this._datasource.disconnect();
        if (this._logPrinter) {
            window.clearInterval(this._logPrinter);
        }
        if (this._flasher) {
            window.clearInterval(this._flasher);
        }
        Object.keys(this._flasherVis).forEach(key => {
            window.clearInterval(this._flasherVis[key])
        })
        this._flasherVis = {}
        this._flashVisQueue.clear()
        this._flashingVisNodes.clear()
    }

    getDataSetOrigin() {
        return {vertices: this._datasource.vertices, edges: this._datasource.edges};
    }

    /**
     * redraw map.
     */
    redraw() {
        const {vertices, edges} = this.getDataSetOrigin()
        this._edges = new DataSet(edges);
        this._nodes = new DataSet(vertices);

        let groups: { [key: string]: {} } = {};

        this._datasource.groups.forEach(group => {
            groups[group] = {
                color: {
                    border: '#000',
                    background: this._randomColor()
                }
            }
        });
        const otherOptions = vertices.length > VIS_VERTEX_MAX ? {
            physics: {
                enabled: true,
                stabilization: {
                    enabled: true,
                    iterations: 100, // 减少迭代次数
                    updateInterval: 50
                },
                solver: 'forceAtlas2Based', // 更适合大规模网络
                forceAtlas2Based: {
                    gravitationalConstant: -50,
                    centralGravity: 0.01,
                    springLength: 100,
                    springConstant: 0.08,
                    damping: 0.4,
                    avoidOverlap: 0.5
                }
            },
            edges: {
                smooth: {
                    type: 'continuous' // 比 'dynamic' 性能更好
                }
            },
            configure: {
                enabled: false // 禁用配置界面提升性能
            },
            layout: {
                improvedLayout: false
            }
        } : {}
        this._graph = new Network(this._mapElement, {
            nodes: this._nodes,
            edges: this._edges
        }, {
            groups,
            interaction: {
                hover: true,
                zoomView: true,
                tooltipDelay: 200,
                // hideEdgesOnDrag: true, // 拖拽时隐藏边提升性能
                hideNodesOnDrag: false
            },
            ...otherOptions
        } as Options);

        this._graph.on('click', async (ev) => {
            this._suggestions.innerText = '';
            this._moveSuggestionSelection('clear');
            if (ev.nodes.length <= 0) {
                return;
            }
            if (this._clickTimer) clearTimeout(this._clickTimer);
            this._clickTimer = window.setTimeout(async () => {
                this.vertexDetails.value = await this._updateInfoPlateWith(ev.nodes[0]);
                this.detailsDialogVisible.value = true
            }, CLICK_DELAY);
        });

        this._graph.on('doubleClick', (ev) => {
            if (ev.nodes.length <= 0) {
                return;
            }
            if (this._clickTimer) {
                clearTimeout(this._clickTimer);
                this._clickTimer = null;
            }
            const nodeId = ev.nodes[0];
            const node = this._nodes.get(nodeId);
            if (node['collapsed']) {
                const {vertices, edges} = this._datasource.newVertices(node)
                vertices.forEach((item: Vertex) => {
                    if (!this._nodes.get(item.id)) {
                        this._nodes.add(item)
                    }
                })
                edges.forEach((edge: Edge) => {
                    if (!this._edges.get({filter: item => item.from === edge.from && item.to === edge.to}).length) {
                        this._edges.add(edge)
                    }
                })
                this._expandNode(nodeId);
            } else {
                this._collapseNode(nodeId);
            }
        });

        const tooltip = document.getElementById('tooltip') as HTMLElement;
        this._graph.on('hoverNode', (ev: HoverNodeEvent) => {
            const nodeId = ev.node;
            const node = this._nodes.get(nodeId) as Vertex;
            if (!node['collapsed']) {
                return
            }
            tooltip.innerHTML = '<strong>Double-click to expand</strong>';
            const {x, y} = ev.pointer.DOM;
            const styles = {
                left: (x) + 'px',
                top: (y) + 'px',
                display: 'block',
                opacity: '1',
                border: '1px red solid',
                position: "absolute",
                borderRadius: '10px',
                padding: '5px',
                backgroundColor: 'antiquewhite',
            };
            Object.assign(tooltip.style, styles);
        });

        this._graph.on('blurNode', () => {
            tooltip.style.display = 'none';
        });

        this._graph.on('stabilizationProgress', (params) => {
            const percent = Math.round((params.iterations / params.total) * 100)
            this.allLoadingInstance?.setText(`${percent}%`)
        })
        this._graph.once('stabilizationIterationsDone', () => {
            this.allLoadingInstance?.close()
        })
    }

    onSubmitFilter = async (term: string) => {
        this._suggestions.innerText = ''
        this._filterInputValue.value = await this._datasource.setSniffFilter(term);
    }
    onSubmitSearch = async (term: string) => {
        this._suggestions.innerText = ''
        let hits = new Set<string>();
        this._lastSearchTerm = term;

        this._findNodes(term).forEach(node => hits.add(node.id));

        this._updateSearchHighlights(hits);
    }
    onPeerActionClick = async (event: MouseEvent) => {
        const target = event.target as HTMLElement;
        // 检查点击的是否是 detail-link
        if (target.classList.contains(CLICK_CLASS.PEER_ACTION_CLASS) || target.closest(`.${CLICK_CLASS.PEER_ACTION_CLASS}`)) {
            event.preventDefault();
            const linkElement = target.classList.contains(CLICK_CLASS.PEER_ACTION_CLASS) ? target : target.closest(`.${CLICK_CLASS.PEER_ACTION_CLASS}`) as HTMLElement;
            let _params = linkElement?.getAttribute('params');
            if (_params) {
                const {node, peer, up} = JSON.parse(_params)
                await this._datasource.setBgpPeers(node, peer, up);
                window.setTimeout(async () => {
                    this.vertexDetails.value = await this._updateInfoPlateWith(node);
                }, 100);
            }
        }
    }
    onConsoleLink = (event: MouseEvent) => {
        const target = event.target as HTMLElement;
        // 检查点击的是否是 detail-link
        if (target.classList.contains(CLICK_CLASS.CONSOLE_CLASS) || target.closest(`.${CLICK_CLASS.CONSOLE_CLASS}`)) {
            event.preventDefault();
            let _params = target?.getAttribute('params');
            if (_params) {
                const {nodeId, label} = JSON.parse(_params)
                this._windowManager.createWindow(nodeId.substr(0, 12), label);
            }
        }
    }
    onNetToggle = async (event: MouseEvent) => {
        const target = event.target as HTMLElement;
        // 检查点击的是否是 detail-link
        if (target.classList.contains(CLICK_CLASS.NET_TOGGLE_CLASS) || target.closest(`.${CLICK_CLASS.NET_TOGGLE_CLASS}`)) {
            event.preventDefault();
            let _params = target?.getAttribute('params');
            if (_params) {
                const {nodeId, netState, nodeRole} = JSON.parse(_params)
                if (netState && nodeRole == 'Host') {
                    let ok = window.confirm('You are about to disconnect a host node. Note that disconnecting nodes flush their routing table - for host nodes, this includes the default route. You will need to manually re-add the default route if you want to re-connect the host.\n\nProceed anyway?');
                    if (!ok) {
                        return;
                    }
                }
                await this._datasource.setNetworkStatus(nodeId, !netState);
                window.setTimeout(async () => {
                    this.vertexDetails.value = await this._updateInfoPlateWith(nodeId);
                }, 100);
            }
        }
    }
    onReloadLink = async (event: MouseEvent) => {
        const target = event.target as HTMLElement;
        // 检查点击的是否是 detail-link
        if (target.classList.contains(CLICK_CLASS.NET_TOGGLE_CLASS) || target.closest(`.${CLICK_CLASS.NET_TOGGLE_CLASS}`)) {
            event.preventDefault();
            let _params = target?.getAttribute('params');
            if (_params) {
                const {nodeId} = JSON.parse(_params)
                this.vertexDetails.value = await this._updateInfoPlateWith(nodeId);
            }
        }
    }
    onLogClear = () => {
        this._logBody.innerText = '';
        this._events = [];
    };
    updateServiceStyle = (service: string, style: {}) => {
        const children = this._nodes.get({
            filter: item => META_CLASS in item.object['Labels'] && item.object['Labels'][META_CLASS] !== '' && JSON.parse(item.object['Labels'][META_CLASS]).includes(service)
        });
        if (children.length === 0) {
            return
        }
        const updates = children.map(child => ({
            id: child.id,
            ...style,
        }));

        this._nodes.update(updates);
    }
}
