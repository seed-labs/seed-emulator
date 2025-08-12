import {DataSet} from 'vis-data';
import {Network, NodeOptions} from 'vis-network';
import {bpfCompletionTree} from '../common/bpf';
import {Completion} from '../common/completion';
import {EmulatorNetwork, EmulatorNode} from '../common/types';
import {WindowManager} from '../common/window-manager';
import {DataSource, NodesType, EdgesType, Vertex, Edge} from './datasource';

/**
 * map UI element bindings.
 */
export interface MapUiConfiguration {
    datasource: DataSource, // data provider
    mapElementId: string, // element id of the map
    infoPlateElementId: string, // element id of the info plate
    filterInputElementId: string, // element id of the filter/search text input
    filterWrapElementId: string, // element id of the filter/search text input wrapper
    logBodyElementId: string, // element id of the log body (the tbody)
    logPanelElementId: string, // element id of the log panel
    logViewportElementId: string, // element id of the log viewport (the table wrapper w/ overflow scroll)
    logWrapElementId: string, // element id of the log wrap (hidden when minimized)
    logControls: { // controls for log
        clearButtonElementId: string, // element id of log clear button
        autoscrollCheckboxElementId: string, // element id of autoscroll checkbox
        disableCheckboxElementId: string, // element id of log disable checkbox
        minimizeToggleElementId: string, // element id of log minimize/unminimize toggle
        minimizeChevronElementId: string // element id of the chevron icon of the log minimize/unminimize toggle
    },
    filterControls: { // filter controls
        filterModeTabElementId: string, // element id of tab for setting mode to filter
        nodeSearchModeTabElementId: string, // element id of tab for setting mode to search
        suggestionsElementId: string // element id of search suggestions
    },
    replayControls: { // replay controls
        recordButtonElementId: string, // element id of record button
        replayButtonElementId: string, // element id of replay button
        stopButtonElementId: string, // element id of stop button
        backwardButtonElementId: string, // element id of backward button
        forwardButtonElementId: string, // element id of forward button
        seekBarElementId: string, // element id of seek bar
        intervalElementId: string, // element id of interval input
        statusElementId: string // element id of status
    },
    windowManager: { // console window manager
        desktopElementId: string, // elementid for desktop
        taskbarElementId: string // elementid for taskbar
    }
}

type FilterMode = 'node-search' | 'filter';

type SuggestionSelectionAction = 'up' | 'down' | 'clear';

interface Event {
    lines: string[],
    source: string
};

interface PlaylistItem {
    nodes: string[],
    at: number
};

const staticDefault = {borderWidth: 1}
const dynamicDefault = {borderWidth: 4}
const arrowStop = {
    to: {enabled: false},
    from: {enabled: false}
};
const arrowTo = {
    to: {enabled: true},
    from: {enabled: false}
};

const arrowFrom = {
    to: {enabled: false},
    from: {enabled: true}
};

const arrowBothWay = {
    to: {enabled: true},
    from: {enabled: true}
};

const extractRequestMacAddresses = (text: string): string[] => {
    const regex = /(?:In|Out)\s+([0-9A-Fa-f]{2}(?:[:-][0-9A-Fa-f]{2}){5}).*?ICMP echo request/g;
    const matches: string[] = [];
    let match = [];
    while ((match = regex.exec(text)) !== null) {
        matches.push(match[1]);
    }
    return matches;
}

const extractReplyMacAddresses = (text: string): string[] => {
    const regex = /(?:In|Out)\s+([0-9A-Fa-f]{2}(?:[:-][0-9A-Fa-f]{2}){5}).*?ICMP echo reply/g;
    const matches: string[] = [];
    let match = [];
    while ((match = regex.exec(text)) !== null) {
        matches.push(match[1]);
    }
    return matches;
}

/**
 * map UI controller.
 */
export class MapUi {
    private _mapElement: HTMLElement;
    private _infoPlateElement: HTMLElement;
    private _filterInput: HTMLInputElement;
    private _filterWrap: HTMLElement;

    private _logPanel: HTMLElement;
    private _logView: HTMLElement;
    private _logWrap: HTMLElement;
    private _logBody: HTMLElement;
    private _logAutoscroll: HTMLInputElement;
    private _logDisable: HTMLInputElement;
    private _logClear: HTMLElement;

    private _filterModeTab: HTMLElement;
    private _searchModeTab: HTMLElement;
    private _suggestions: HTMLElement;

    private _logToggle: HTMLElement;
    private _logToggleChevron: HTMLElement;

    private _replayButton: HTMLButtonElement;
    private _recordButton: HTMLButtonElement;
    private _forwardButton: HTMLButtonElement;
    private _backwardButton: HTMLButtonElement;
    private _stopButton: HTMLButtonElement;
    private _replaySeekBar: HTMLInputElement;
    private _interval: HTMLInputElement;
    private _replayStatusText: HTMLElement;

    private _datasource: DataSource;

    private _nodes: NodesType;
    private _edges: EdgesType;
    private _graph: Network;

    /** list of log elements to be rendered to log body */
    private _logQueue: HTMLElement[];

    /** set of vertex ids scheduled for flashing */
    private _flashQueue: Set<string>;
    /** set of vertex ids scheduled for un-flash */
    private _flashingNodes: Set<string>;
    // vis
    private _visSetQueue: Set<string>;
    private _flashVisQueue: Set<string>;
    private _flashingVisNodes: Set<string>;
    private _tFlashNodeMapping: { [key: string]: Set<string> };
    private _visFlashNodeMapping: { [key: string]: Set<string> };
    private _tVisFlashNodeMapping: { [key: string]: Set<string> };
    private _visArrowMapping: { [key: string]: Set<string> };
    private _tVisArrowMapping: { [key: string]: Set<string> };

    private _logPrinter: number;
    private _flasher: number;
    private _flasherVis: { [key: string]: number };

    private _macMapping: { [mac: string]: string };
    private _macContainerIDMapping: { [mac: string]: string };

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

    /**
     * Build a new map UI controller.
     *
     * @param config element bindings.
     */
    constructor(config: MapUiConfiguration) {
        this._datasource = config.datasource;
        this._mapElement = document.getElementById(config.mapElementId);
        this._infoPlateElement = document.getElementById(config.infoPlateElementId);
        this._filterInput = document.getElementById(config.filterInputElementId) as HTMLInputElement;
        this._filterWrap = document.getElementById(config.filterWrapElementId);

        this._logPanel = document.getElementById(config.logPanelElementId);
        this._logView = document.getElementById(config.logViewportElementId);
        this._logWrap = document.getElementById(config.logWrapElementId);
        this._logBody = document.getElementById(config.logBodyElementId);
        this._logAutoscroll = document.getElementById(config.logControls.autoscrollCheckboxElementId) as HTMLInputElement;
        this._logDisable = document.getElementById(config.logControls.disableCheckboxElementId) as HTMLInputElement;
        this._logClear = document.getElementById(config.logControls.clearButtonElementId);

        this._filterModeTab = document.getElementById(config.filterControls.filterModeTabElementId);
        this._searchModeTab = document.getElementById(config.filterControls.nodeSearchModeTabElementId);
        this._suggestions = document.getElementById(config.filterControls.suggestionsElementId);

        this._logToggle = document.getElementById(config.logControls.minimizeToggleElementId);
        this._logToggleChevron = document.getElementById(config.logControls.minimizeChevronElementId);

        this._replayButton = document.getElementById(config.replayControls.replayButtonElementId) as HTMLButtonElement;
        this._recordButton = document.getElementById(config.replayControls.recordButtonElementId) as HTMLButtonElement;
        this._stopButton = document.getElementById(config.replayControls.stopButtonElementId) as HTMLButtonElement;
        this._forwardButton = document.getElementById(config.replayControls.forwardButtonElementId) as HTMLButtonElement;
        this._backwardButton = document.getElementById(config.replayControls.backwardButtonElementId) as HTMLButtonElement;
        this._replaySeekBar = document.getElementById(config.replayControls.seekBarElementId) as HTMLInputElement;
        this._interval = document.getElementById(config.replayControls.intervalElementId) as HTMLInputElement;
        this._replayStatusText = document.getElementById(config.replayControls.statusElementId);

        this._intervalDefault = 500;
        this._flashVisStyleMapping = {};

        this._logMinimized = true;

        this._replayStatus = 'stopped';
        this._events = [];
        this._recording = false;
        this._seeking = false;
        this._playlist = [];

        this._suggestionsSelection = -1;

        this._logQueue = [];

        this._flashQueue = new Set<string>();
        this._flashingNodes = new Set<string>();
        this._flashVisQueue = new Set<string>();
        this._flashingVisNodes = new Set<string>();
        this._flasherVis = {};
        this._visSetQueue = new Set<string>();
        this._tFlashNodeMapping = {src: new Set<string>(), dst: new Set<string>()};
        this._visFlashNodeMapping = {src: new Set<string>(), dst: new Set<string>()};
        this._tVisFlashNodeMapping = {src: new Set<string>(), dst: new Set<string>()};
        this._visArrowMapping = {to: new Set<string>(), from: new Set<string>(), both: new Set<string>()};
        this._tVisArrowMapping = {to: new Set<string>(), from: new Set<string>(), both: new Set<string>()};

        this._searchHighlightNodes = new Set<string>();

        this._macMapping = {};
        this._macContainerIDMapping = {};

        this._filterMode = 'filter';
        this._lastSearchTerm = '';

        this._windowManager = new WindowManager(config.windowManager.desktopElementId, config.windowManager.taskbarElementId);

        this._bpfCompletion = new Completion(bpfCompletionTree);

        this._replayButton.onclick = () => {
            this._replayPlayPause();
        };

        this._stopButton.onclick = () => {
            this._replayStop();
        };

        this._recordButton.onclick = () => {
            this._recordStartStop();
        };

        this._forwardButton.onclick = () => {
            this._replaySeek(1);
        };

        this._backwardButton.onclick = () => {
            this._replaySeek(-1);
        };

        this._replaySeekBar.onchange = () => {
            this._replaySeek(Number.parseInt(this._replaySeekBar.value), true);
        };

        this._replaySeekBar.onmousedown = () => {
            this._seeking = true;
        };

        this._replaySeekBar.onmouseup = () => {
            this._seeking = false;
        };

        this._logToggle.onclick = () => {
            if (this._logMinimized) {
                this._logWrap.classList.remove('minimized');
                this._logToggleChevron.className = 'bi bi-chevron-down';
            } else {
                this._logWrap.classList.add('minimized');
                this._logToggleChevron.className = 'bi bi-chevron-up';
            }

            this._logMinimized = !this._logMinimized;
        };

        this._filterInput.onkeydown = (event) => {
            if (event.key == 'ArrowUp') {
                this._moveSuggestionSelection('up');
                this._ignoreKeyUp = true;

                return false;
            }

            if (event.key == 'ArrowDown') {
                this._moveSuggestionSelection('down');
                this._ignoreKeyUp = true;

                return false;
            }

            if (event.key == 'Tab' && this._suggestionsSelection == -1) {
                this._ignoreKeyUp = true;

                if (this._suggestions.children.length > 0) {
                    (this._suggestions.children[0] as HTMLElement).click();
                }

                return false;
            }

            if ((event.key == 'Enter' || event.key == 'Tab') && this._suggestionsSelection != -1) {
                (this._suggestions.children[this._suggestionsSelection] as HTMLElement).click();
                this._ignoreKeyUp = true;

                return false;
            }

            this._ignoreKeyUp = false;
        };

        this._filterInput.onkeyup = (event) => {
            if (this._ignoreKeyUp) {
                return; // fixme: preventDefault / stopPropagation does not work?
            }

            this._filterUpdateHandler(event);
        };

        this._searchModeTab.onclick = () => {
            this._setFilterMode('node-search');
        };

        this._filterModeTab.onclick = () => {
            this._setFilterMode('filter');
        };

        this._logClear.onclick = () => {
            this._logBody.innerText = '';
            this._events = [];
        };

        this._filterInput.onclick = () => {
            this._updateFilterSuggestions(this._filterInput.value);
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
                    let nodeId = this._macMapping[mac];

                    if (this._nodes.get(nodeId) === null) {
                        return;
                    }
                    this._flashQueue.add(nodeId);
                    // this._flashVisQueue.add(nodeId);
                }
            });

            let netNodeRequest = new Set();
            let netNodeReply = new Set();
            extractRequestMacAddresses(data.data).forEach(mac => {
                netNodeRequest.add(this._macMapping[mac]);
            })
            extractReplyMacAddresses(data.data).forEach(mac => {
                netNodeReply.add(this._macMapping[mac]);
            })
            const IPs = data.data.match(/([0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}) > ([0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}): ICMP echo request/);
            const IPsReply = data.data.match(/([0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}) > ([0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}): ICMP echo reply/);

            // at least one mac address matching a net is found, flash the node.
            // note: when no matching net is found, the "packet" may not be a
            // packet, but output from tcpdump.
            if (flashed.size > 0) {
                const nodeId = data.source;
                if (this._visSetQueue.has(nodeId)) {
                    this._flashVisQueue.add(nodeId);
                    if (IPs) {
                        this._visFlashNodeMapping.src.add(this._datasource.getNodeInfoByIP(IPs[1]).Id);
                    }
                } else {
                    this._flashQueue.add(nodeId);
                }
                let src: string, dst: string;
                if (IPs) {
                    src = this._datasource.getNodeInfoByIP(IPs[1]).Id;
                    dst = this._datasource.getNodeInfoByIP(IPs[2]).Id;
                } else if (IPsReply) {
                    src = this._datasource.getNodeInfoByIP(IPsReply[2]).Id;
                    dst = this._datasource.getNodeInfoByIP(IPsReply[1]).Id;
                }
                if (netNodeRequest.size > 0) {
                    let tEdge = this._findEdgeId2(nodeId, [...netNodeRequest][0]);
                    if (src === nodeId) {
                        this._visArrowMapping.to.add(tEdge);
                    } else {
                        this._visArrowMapping.from.add(tEdge);
                    }
                }
                if (netNodeRequest.size > 1) {
                    this._visArrowMapping.to.add(this._findEdgeId2(nodeId, [...netNodeRequest][1]))
                }

                if (netNodeReply.size > 0) {
                    let tEdge = this._findEdgeId2(nodeId, [...netNodeReply][0]);
                    if (dst === nodeId) {
                        if (this._visArrowMapping.from.has(tEdge)) {
                            this._visArrowMapping.from.delete(tEdge);
                            this._visArrowMapping.both.add(tEdge);
                        } else {
                            this._visArrowMapping.to.add(tEdge);
                        }
                    } else {
                        if (this._visArrowMapping.to.has(tEdge)) {
                            this._visArrowMapping.to.delete(tEdge);
                            this._visArrowMapping.both.add(tEdge);
                        } else {
                            this._visArrowMapping.from.add(tEdge);
                        }
                    }
                }
                if (netNodeReply.size > 1) {
                    let tEdge = this._findEdgeId2(nodeId, [...netNodeReply][1]);
                    if (this._visArrowMapping.from.has(tEdge)) {
                        this._visArrowMapping.from.delete(tEdge);
                        this._visArrowMapping.both.add(tEdge);
                    } else {
                        this._visArrowMapping.to.add(tEdge)
                    }
                }
            }

            let now = new Date();
            let lines: string[] = data.data.split('\r\n').filter(line => line !== '');

            if (lines.length > 0 && this._recording) {
                this._events.push({lines: lines, source: data.source});
            }

            // tcpdump output: "listening on xxx", meaning tcpdump is running
            // and the last expressions does not contain error.
            if (data.data.includes('listening')) {
                this._filterInput.classList.remove('error');
                this._filterWrap.classList.remove('error');
            }

            // tcpdump output: "error", meaning tcpdump don't like the last
            // expression
            if (data.data.includes('error')) {
                this._filterInput.classList.add('error');
                this._filterWrap.classList.add('error');
            }

            if (this._logDisable.checked) {
                return;
            }

            let node = this._nodes.get(data.source as string);

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
                this._focusNode(node.id);
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
        });
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
        this._tVisArrowMapping.from = new Set(this._visArrowMapping.from);
        this._tVisArrowMapping.to = new Set(this._visArrowMapping.to);
        this._tVisArrowMapping.both = new Set(this._visArrowMapping.both);
        this._visArrowMapping.from.clear();
        this._visArrowMapping.to.clear();
        this._visArrowMapping.both.clear();

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
        let updateFromRequestEdge = Array.from(this._tVisArrowMapping.from).map(nodeId => {
            return {
                id: nodeId,
                arrows: arrowFrom
            }
        });
        let updateToRequestEdge = Array.from(this._tVisArrowMapping.to).map(nodeId => {
            return {
                id: nodeId,
                arrows: arrowTo
            }
        });

        let updateBothEdge = Array.from(this._tVisArrowMapping.both).map(nodeId => {
            return {
                id: nodeId,
                arrows: arrowBothWay
            }
        });

        this._edges.update(updateFromRequestEdge);
        this._edges.update(updateToRequestEdge);
        this._edges.update(updateBothEdge);
        this._nodes.update(updateRequest);

        // schedule un-flash
        window.setTimeout(() => {
            let updateRequest = Array.from(this._flashingNodes).map(nodeId => {
                return {
                    id: nodeId, ...staticDefault
                }
            });
            let updateRequestEdge = Array.from(new Set([...this._tVisArrowMapping.from, ...this._tVisArrowMapping.to, ...this._tVisArrowMapping.both])).map(nodeId => {
                return {
                    id: nodeId,
                    arrows: arrowStop
                }
            });

            this._nodes.update(updateRequest);
            this._edges.update(updateRequestEdge)
            this._flashingNodes.clear();
            this._tFlashNodeMapping.src.clear();
            this._tFlashNodeMapping.dst.clear();
        }, 300);
    }

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
            case 'flash':
                return this._flashVisNodesFlashKeep(nodeId, _static, dynamic, interval);
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
        let updateRequestEdge = Array.from(updateEdgeIds).map(nodeId => {
            return {
                id: nodeId,
                arrows: arrowStop
            }
        });
        this._edges.update(updateRequestEdge)

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

                this._tVisFlashNodeMapping.src = new Set(this._visFlashNodeMapping.src);
                this._visFlashNodeMapping.src.delete(nodeId);

                this._findEdgeIds(nodeId).forEach(edgeId => updateEdgeIds.add(edgeId));
                let updateRequestEdge = Array.from(updateEdgeIds).map(edgeId => {
                    if (this._tVisFlashNodeMapping.src.has(nodeId)) {
                        return {
                            id: edgeId,
                            arrows: arrowTo
                        }
                    } else {
                        return {
                            id: edgeId,
                            arrows: arrowFrom
                        }
                    }
                });

                this._nodes.update({
                    id: nodeId, ...dynamic
                });
                this._edges.update(updateRequestEdge)

                this._flashingVisNodes.clear();
                this._tVisFlashNodeMapping.src.clear();
            }, interval);
        }
    }

    private _flashVisNodesFlashKeep(nodeId: string, _static: {}, dynamic: {}, interval: number) {
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
     * update mode to filter or search.
     *
     * @param mode new filter mode.
     */
    private async _setFilterMode(mode: FilterMode) {
        if (mode == this._filterMode) {
            return;
        }

        this._filterMode = mode;

        this._suggestions.innerText = '';
        this._moveSuggestionSelection('clear');

        if (mode == 'filter') {
            this._updateSearchHighlights(new Set<string>()); // empty search highligths
            this._filterInput.value = await this._datasource.getSniffFilter();
            this._filterInput.placeholder = 'Type a BPF expression to animate packet flows on the map...';
            this._filterModeTab.classList.remove('inactive');
            this._searchModeTab.classList.add('inactive');
        }

        if (mode == 'node-search') {
            this._filterInput.value = this._lastSearchTerm;
            this._filterInput.placeholder = 'Search networks and nodes...';
            this._filterModeTab.classList.add('inactive');
            this._searchModeTab.classList.remove('inactive');
            this._filterUpdateHandler(null, true);
        }
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

        let current = children[this._suggestionsSelection];
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
    private _updateFilterSuggestions(term: string) {
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
                    this._filterInput.value += `${fillText} `;
                    this._moveSuggestionSelection('clear');
                    this._updateFilterSuggestions(this._filterInput.value);
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
        let term = this._filterInput.value;

        if (((!event || event.key != 'Enter') && !forced)) {
            this._moveSuggestionSelection('clear');
            this._suggestions.innerText = '';
            this._updateFilterSuggestions(term);

            return;
        }

        this._suggestions.innerText = '';

        if (this._filterMode == 'filter') {
            this._filterInput.value = await this._datasource.setSniffFilter(term);
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

    /**
     * update infoplate with node.
     *
     * @param nodeId node id for any vertex (can be node or net).
     */
    private async _updateInfoPlateWith(nodeId: string) {
        let vertex = this._nodes.get(nodeId);

        this._curretNode = vertex;

        let infoPlate = document.createElement('div');
        this._infoPlateElement.classList.add('loading');

        let title = document.createElement('div');
        title.className = 'title';
        infoPlate.appendChild(title);

        if (vertex.type == 'network') {
            let net = vertex.object as EmulatorNetwork;
            title.innerText = `${net.meta.emulatorInfo.type == 'global' ? 'Exchange' : 'Network'}: ${vertex.label}`;

            if (net.meta.emulatorInfo.description) {
                let div = document.createElement('div');
                div.innerText = net.meta.emulatorInfo.description;
                div.classList.add('description');

                infoPlate.appendChild(div);
            }

            infoPlate.appendChild(this._createInfoPlateValuePair('ID', net.Id.substr(0, 12)));
            infoPlate.appendChild(this._createInfoPlateValuePair('Name', net.meta.emulatorInfo.name));
            infoPlate.appendChild(this._createInfoPlateValuePair('Scope', net.meta.emulatorInfo.scope));
            infoPlate.appendChild(this._createInfoPlateValuePair('Type', net.meta.emulatorInfo.type));
            infoPlate.appendChild(this._createInfoPlateValuePair('Prefix', net.meta.emulatorInfo.prefix));
        }

        if (vertex.type == 'node') {
            let node = vertex.object as EmulatorNode;
            title.innerText = `${['Router', 'BorderRouter'].includes(node.meta.emulatorInfo.role) ? 'Router' : 'Host'}: ${vertex.label}`;

            if (node.meta.emulatorInfo.description) {
                let div = document.createElement('div');
                div.innerText = node.meta.emulatorInfo.description;
                div.classList.add('description');

                infoPlate.appendChild(div);
            }

            infoPlate.appendChild(this._createInfoPlateValuePair('ID', node.Id.substr(0, 12)));
            infoPlate.appendChild(this._createInfoPlateValuePair('ASN', node.meta.emulatorInfo.asn.toString()));
            infoPlate.appendChild(this._createInfoPlateValuePair('Name', node.meta.emulatorInfo.name));
            infoPlate.appendChild(this._createInfoPlateValuePair('Role', node.meta.emulatorInfo.role));

            let ipAddresses = document.createElement('div');
            ipAddresses.classList.add('section');

            let ipTitle = document.createElement('div');
            ipTitle.className = ' title';
            ipTitle.innerText = 'IP addresses';

            ipAddresses.appendChild(ipTitle);

            node.meta.emulatorInfo.nets.forEach(net => {
                ipAddresses.appendChild(this._createInfoPlateValuePair(net.name, net.address));
            });

            infoPlate.appendChild(ipAddresses);

            if (['Router', 'Route Server', 'BorderRouter'].includes(node.meta.emulatorInfo.role)) {
                let bgpDetails = document.createElement('div');
                bgpDetails.classList.add('section');

                let peers = await this._datasource.getBgpPeers(node.Id);

                let bgpTitle = document.createElement('div');
                bgpTitle.className = 'title';
                bgpTitle.innerText = 'BGP sessions';

                bgpDetails.appendChild(bgpTitle);

                if (peers.length == 0) {
                    let noPeers = document.createElement('div');
                    noPeers.innerText = 'No BGP peers.';
                    noPeers.classList.add('caption');

                    bgpDetails.appendChild(noPeers);
                }

                peers.forEach(peer => {
                    let container = document.createElement('div');

                    let peerName = document.createElement('span');
                    peerName.classList.add('label');
                    peerName.innerText = peer.name;

                    let peerStatus = document.createElement('span');
                    peerStatus.innerText = peer.protocolState != 'down' ? peer.bgpState : 'Disabled';

                    let peerAction = document.createElement('a');

                    peerAction.href = '#';
                    peerAction.classList.add('inline-action-link');
                    peerAction.innerText = peer.protocolState != 'down' ? 'Disable' : 'Enable';
                    peerAction.onclick = async () => {
                        await this._datasource.setBgpPeers(node.Id, peer.name, peer.protocolState == 'down');
                        this._infoPlateElement.classList.add('loading');
                        window.setTimeout(() => {
                            this._updateInfoPlateWith(node.Id);
                        }, 100);
                    };

                    container.appendChild(peerName);
                    container.appendChild(peerStatus);
                    container.appendChild(peerAction);

                    bgpDetails.appendChild(container);
                });

                infoPlate.appendChild(bgpDetails);
            }

            let actions = document.createElement('div');
            actions.classList.add('section');

            let actionTitle = document.createElement('div');
            actionTitle.className = 'title';
            actionTitle.innerText = 'Actions';

            actions.appendChild(actionTitle);

            let consoleLink = document.createElement('a');

            consoleLink.href = '#';
            consoleLink.innerText = 'Launch console';
            consoleLink.classList.add('action-link');

            consoleLink.onclick = () => {
                this._windowManager.createWindow(node.Id.substr(0, 12), vertex.label);
            };

            let netToggle = document.createElement('a');
            let netState = await this._datasource.getNetworkStatus(node.Id);

            netToggle.href = '#';
            netToggle.innerText = netState ? 'Disconnect' : 'Re-connect';
            netToggle.onclick = async () => {
                if (netState && node.meta.emulatorInfo.role == 'Host') {
                    let ok = window.confirm('You are about to disconnect a host node. Note that disconnecting nodes flush their routing table - for host nodes, this includes the default route. You will need to manually re-add the default route if you want to re-connect the host.\n\nProceed anyway?');
                    if (!ok) {
                        return;
                    }
                }
                await this._datasource.setNetworkStatus(node.Id, !netState);
                this._infoPlateElement.classList.add('loading');
                window.setTimeout(() => {
                    this._updateInfoPlateWith(node.Id);
                }, 100);
            };
            netToggle.classList.add('action-link');

            let reloadLink = document.createElement('a');

            reloadLink.href = '#';
            reloadLink.innerText = 'Refresh';
            reloadLink.classList.add('action-link');
            reloadLink.onclick = () => {
                this._updateInfoPlateWith(node.Id);
            };

            actions.append(consoleLink);
            actions.append(netToggle);
            actions.append(reloadLink);

            infoPlate.appendChild(actions);
        }

        this._infoPlateElement.innerText = '';
        this._infoPlateElement.appendChild(infoPlate);
        this._infoPlateElement.classList.remove('loading');
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
            this._replayButton.innerHTML = this._replayStatus === 'playing' ? '<i class="bi bi-pause"></i>' : '<i class="bi bi-play-fill"></i>';
            this._recordButton.innerHTML = '<i class="bi bi-record-fill"></i>';
        }

        if (this._replayStatus === 'stopped') {
            this._replayButton.disabled = this._recording;
            this._recordButton.disabled = false;
            this._stopButton.disabled = true;
            this._forwardButton.disabled = true;
            this._backwardButton.disabled = true;
            this._replaySeekBar.disabled = true;
            this._interval.disabled = false;

            this._replayButton.innerHTML = '<i class="bi bi-play-fill"></i>';
            this._recordButton.innerHTML = this._recording ? '<i class="bi bi-stop-fill"></i>' : '<i class="bi bi-record-fill"></i>';
        }
    }

    /**
     * stop replay
     */
    private _replayStop() {
        if (this._replayStatus === 'stopped') {
            return;
        }

        this._replayStatus = 'stopped';
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
        this._replayStatusText.innerText = 'Replay stopped.';
    }

    /**
     * seek to a specific time
     * @param offset offset from current time.
     * @param absolute offset is absolute time.
     */
    private _replaySeek(offset: number, absolute: boolean = false) {
        if (this._replayStatus === 'stopped') {
            return;
        }

        this._replayStatus = 'paused';
        this._updateReplayControls();

        if (absolute) {
            this._replayPos = offset;
        } else {
            this._replayPos += offset;
        }

        this._doReplay(true);
    }

    /**
     * toggle recording.
     */
    private _recordStartStop() {
        if (this._replayStatus !== 'stopped') {
            return;
        }

        if (this._recording) {
            this._recording = false;
            this._replayStatusText.innerText = 'Replay stopped.';
            this._recordButton.innerHTML = '<i class="bi bi-stop-fill"></i>';
            this._updateReplayControls();
        } else {
            this._events = [];
            this._recording = true;
            this._replayStatusText.innerText = 'Recording events...';
            this._recordButton.innerHTML = '<i class="bi bi-record-fill"></i>';
            this._updateReplayControls();
        }
    }

    private _buildPlayList(): PlaylistItem[] {
        let refDate = new Date();

        let playlist: PlaylistItem[] = [];

        this._events.forEach(e => {
            e.lines.forEach(line => {
                let time = line.split(' ')[0];
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

    /**
     * toggle play / pause replay.
     */
    private _replayPlayPause() {
        if (this._recording) {
            return;
        }

        if (this._replayStatus === 'stopped') {
            this._replayPos = 0;
            this._replayStatusText.innerText = 'Replay stopped.';
            this._replayStatus = 'playing';
            this._playlist = this._buildPlayList();
            this._doReplay();
            this._updateReplayControls();
        } else if (this._replayStatus === 'playing') {
            this._replayStatus = 'paused';
            this._updateReplayControls();
        } else if (this._replayStatus === 'paused') {
            this._replayStatus = 'playing';
            this._updateReplayControls();
        }
    }

    private _doReplay(once: boolean = false) {
        // not playing.
        if (this._replayStatus === 'stopped') {
            return;
        }

        if (!once) {
            this._replayTask = window.setTimeout(() => this._doReplay(), Number.parseInt(this._interval.value));
        }

        this._replayStatusText.innerText = `${this._replayStatus === 'paused' ? 'Paused' : 'Playing'}: ${this._replayPos}/${this._playlist.length} event(s) left.`;

        if (!this._seeking) {
            this._replaySeekBar.value = this._replayPos.toString();
        }

        // reached the end.
        if (this._replayPos >= this._playlist.length) {
            this._replayStatus = 'paused';
            this._replayStatusText.innerText = 'End of record.';
            this._replaySeekBar.value = '0';
            this._replayPos = 0;
            this._updateReplayControls();
            return;
        }

        // un-flash nodes.
        let unflashRequest = Array.from(this._flashingNodes).map(nodeId => {
            let style;
            if (this._flashVisStyleMapping.hasOwnProperty(nodeId)) {
                style = this._flashVisStyleMapping[nodeId].static;
            } else {
                style = staticDefault;
            }
            return {
                id: nodeId, ...style
            }
        });
        this._nodes.update(unflashRequest);
        this._flashingNodes.clear();
        this._flashingVisNodes.clear();

        // flash nodes from this event.
        let current = this._playlist[this._replayPos];
        current.nodes.forEach(node => this._flashingNodes.add(node));
        let flashRequest = Array.from(this._flashingNodes).map(nodeId => {
            let style;
            if (this._flashVisStyleMapping.hasOwnProperty(nodeId)) {
                style = this._flashVisStyleMapping[nodeId].dynamic;
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

    /**
     * connect datasource, start mapping, and start the log/flash workers.
     */
    async start() {
        await this._datasource.connect();
        this.redraw();
        this._mapMacAddresses();

        if (this._filterMode == 'filter') {
            this._filterInput.value = await this._datasource.getSniffFilter();
        }

        this._logPrinter = window.setInterval(() => {
            var scroll = false;

            while (this._logQueue.length > 0) {
                scroll = true;
                this._logBody.appendChild(this._logQueue.shift());
            }

            if (scroll && this._logAutoscroll.checked && !this._logDisable.checked) {
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
        window.clearInterval(this._logPrinter);
        window.clearInterval(this._flasher);
        Object.keys(this._flasherVis).forEach(key => {
            window.clearInterval(this._flasherVis[key])
        })
        this._flasherVis = {}
        this._flashVisQueue.clear()
        this._flashingVisNodes.clear()
    }

    /**
     * redraw map.
     */
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

        let interaction = {
            hover: true
        };
        let locales = {
            en: {
                edit: 'Edit',
                del: 'Delete selected',
                back: 'Back',
                addNode: 'Add Node',
                addEdge: 'Add Edge',
                editNode: 'Edit Node',
                editEdge: 'Edit Edge',
                addDescription: 'Click in an empty space to place a new node.',
                edgeDescription: 'Click on a node and drag the edge to another node to connect them.',
                editEdgeDescription: 'Click on the control points and drag them to a node to connect to it.',
                createEdgeError: 'Cannot link edges to a cluster.',
                deleteClusterError: 'Clusters cannot be deleted.',
                editClusterError: 'Clusters cannot be edited.'
            }
        };
        let configure = {
            enabled: true,
            filter: 'nodes,edges',
            // container: undefined,
            showButton: true
        }
        let edges = {
            arrows: {
                to: {
                    enabled: false,
                    // imageHeight: undefined,
                    // imageWidth: undefined,
                    scaleFactor: 1,
                    // src: undefined,
                    type: "arrow"
                },
                middle: {
                    enabled: false,
                    // imageHeight: 32,
                    // imageWidth: 32,
                    scaleFactor: 1,
                    // src: "https://visjs.org/images/visjs_logo.png",
                    // type: "image"
                    type: "arrow"
                },
                from: {
                    enabled: false,
                    // imageHeight: undefined,
                    // imageWidth: undefined,
                    scaleFactor: 1,
                    // src: undefined,
                    type: "arrow"
                }
            },
            endPointOffset: {
                from: 0,
                to: 0
            },
            arrowStrikethrough: true,
            chosen: true,
            color: {
                color: '#848484',
                highlight: '#848484',
                hover: '#848484',
                inherit: 'from',
                opacity: 1.0
            },
            dashes: false,
            font: {
                color: '#343434',
                size: 14, // px
                face: 'arial',
                background: 'none',
                strokeWidth: 2, // px
                strokeColor: '#ffffff',
                align: 'horizontal',
                multi: false,
                vadjust: 0,
                bold: {
                    color: '#343434',
                    size: 14, // px
                    face: 'arial',
                    vadjust: 0,
                    mod: 'bold'
                },
                ital: {
                    color: '#343434',
                    size: 14, // px
                    face: 'arial',
                    vadjust: 0,
                    mod: 'italic',
                },
                boldital: {
                    color: '#343434',
                    size: 14, // px
                    face: 'arial',
                    vadjust: 0,
                    mod: 'bold italic'
                },
                mono: {
                    color: '#343434',
                    size: 15, // px
                    face: 'courier new',
                    vadjust: 2,
                    mod: ''
                }
            },
            hidden: false,
            hoverWidth: 1.5,
            // label: undefined,
            labelHighlightBold: true,
            // length: undefined,
            physics: true,
            scaling: {
                min: 1,
                max: 15,
                label: {
                    enabled: true,
                    min: 14,
                    max: 30,
                    maxVisible: 30,
                    drawThreshold: 5
                },
                customScalingFunction: function (min, max, total, value) {
                    if (max === min) {
                        return 0.5;
                    } else {
                        var scale = 1 / (max - min);
                        return Math.max(0, (value - min) * scale);
                    }
                }
            },
            selectionWidth: 1,
            selfReference: {
                size: 20,
                angle: Math.PI / 4,
                renderBehindTheNode: true
            },
            shadow: {
                enabled: false,
                color: 'rgba(0,0,0,0.5)',
                size: 10,
                x: 5,
                y: 5
            },
            smooth: {
                enabled: true,
                type: "dynamic",
                roundness: 0.5
            },
            // title: undefined,
            // value: undefined,
            width: 1,
            widthConstraint: false
        }
        let nodes = {
            borderWidth: 1,
            borderWidthSelected: 2,
            // brokenImage: undefined,
            chosen: true,
            color: {
                border: '#2B7CE9',
                background: '#97C2FC',
                highlight: {
                    border: '#2B7CE9',
                    background: '#D2E5FF'
                },
                hover: {
                    border: '#2B7CE9',
                    background: '#D2E5FF'
                }
            },
            opacity: 1,
            fixed: {
                x: false,
                y: false
            },
            font: {
                color: '#343434',
                size: 14, // px
                face: 'arial',
                background: 'none',
                strokeWidth: 0, // px
                strokeColor: '#ffffff',
                align: 'center',
                multi: false,
                vadjust: 0,
                bold: {
                    color: '#343434',
                    size: 14, // px
                    face: 'arial',
                    vadjust: 0,
                    mod: 'bold'
                },
                ital: {
                    color: '#343434',
                    size: 14, // px
                    face: 'arial',
                    vadjust: 0,
                    mod: 'italic',
                },
                boldital: {
                    color: '#343434',
                    size: 14, // px
                    face: 'arial',
                    vadjust: 0,
                    mod: 'bold italic'
                },
                mono: {
                    color: '#343434',
                    size: 15, // px
                    face: 'courier new',
                    vadjust: 2,
                    mod: ''
                }
            },
            // group: undefined,
            heightConstraint: false,
            hidden: false,
            icon: {
                face: 'FontAwesome',
                // code: undefined,
                // weight: undefined,
                size: 50,  //50,
                color: '#2B7CE9'
            },
            // image: undefined,
            imagePadding: {
                left: 0,
                top: 0,
                bottom: 0,
                right: 0
            },
            // label: undefined,
            labelHighlightBold: true,
            // level: undefined,
            mass: 1,
            physics: true,
            scaling: {
                min: 10,
                max: 30,
                label: {
                    enabled: false,
                    min: 14,
                    max: 30,
                    maxVisible: 30,
                    drawThreshold: 5
                },
                customScalingFunction: function (min, max, total, value) {
                    if (max === min) {
                        return 0.5;
                    } else {
                        let scale = 1 / (max - min);
                        return Math.max(0, (value - min) * scale);
                    }
                }
            },
            shadow: {
                enabled: false,
                color: 'rgba(0,0,0,0.5)',
                size: 10,
                x: 5,
                y: 5
            },
            shape: 'ellipse',
            shapeProperties: {
                borderDashes: false, // only for borders
                borderRadius: 6,     // only for box shape
                interpolation: false,  // only for image and circularImage shapes
                useImageSize: false,  // only for image and circularImage shapes
                useBorderWithImage: false,  // only for image shape
                coordinateOrigin: 'center'  // only for image and circularImage shapes
            },
            size: 25,
            // title: undefined,
            // value: undefined,
            widthConstraint: false,
            // x: undefined,
            // y: undefined
        }

        this._graph = new Network(this._mapElement, {
            nodes: this._nodes,
            edges: this._edges
        }, {
            groups,
            interaction,
            locales,
            configure,
            nodes,
            edges,
        });

        this._graph.on('click', (ev) => {
            this._suggestions.innerText = '';
            this._moveSuggestionSelection('clear');

            if (ev.nodes.length <= 0) {
                return;
            }

            this._updateInfoPlateWith(ev.nodes[0]);
        });

        // this._graph.on("dragStart", () => {
        //     this._graph.setOptions({physics: false});
        // });
        // this._graph.on("dragEnd", () => {
        //     this._graph.setOptions({physics: false});
        // });
    }
}
