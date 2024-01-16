import { DataSet } from 'vis-data';
import { Network } from 'vis-network';
import { bpfCompletionTree } from '../common/bpf';
import { Completion } from '../common/completion';
import { EmulatorNetwork, EmulatorNode } from '../common/types';
import { WindowManager } from '../common/window-manager';
import { DataSource, Edge, Vertex } from './datasource';

/**
 * map UI element bindings.
 */
export interface MapUiConfiguration {
    datasource: DataSource, // data provider
    mapElementId: string, // element id of the map 
    infoPlateElementId: string, // element id of the info plate
    connPlateElementId: string, // element id of the connectivity plate

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
    movementControls: {
        resetButtonElementId: string,
        backwardButtonElementId: string, 
        forwardButtonElementId: string,
        statusElementId: string
    }
    connControls: {
        connFromElementId: string, // element id of from_node
        connToElementId: string, // element id of to_node
        connDistElementId: string, // element id of dist
        connLossElementId: string, // element id of loss
        connTestButtonElementId: string, //element id of test button
        showLossCheckBoxElementId: string,
        showDistanceCheckBoxElementId: string
        connResultElementId: string, //element id of conn result
    }
    // filePathControls: {
    //     submitButtonElementId: string, // element id of file path submit button
    //     filePathInputElementId: string // element id of file path input 
    // }
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

/**
 * map UI controller.
 */
export class MapUi {
    private _mapElement: HTMLElement;
    private _infoPlateElement: HTMLElement;
    private _connPlateElement: HTMLElement;
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

    private _resetMoveButton: HTMLButtonElement;
    private _moveForwardButton: HTMLButtonElement;
    private _moveBackwardButton: HTMLButtonElement;
    private _movementStatusText: HTMLElement;

    private _connFromText: HTMLElement;
    private _connToText: HTMLElement;
    private _connDistanceText: HTMLElement;
    private _connLossText: HTMLElement;
    private _connResultText: HTMLElement;
    private _connTestButton: HTMLButtonElement;
    private _showLossCheckBox: HTMLInputElement;
    private _showDistanceCheckBox: HTMLInputElement;

    // private _filepathSubmitButton: HTMLButtonElement;
    // private _filepathInput: HTMLInputElement;
    // private _node_info_filepath: string;

    private _datasource: DataSource;

    private _nodes: DataSet<Vertex, 'id'>;
    private _buildings: DataSet<Vertex, 'id'>;
    private _edges: DataSet<Edge, 'id'>;
    private _tmp_edges: Edge[] = [];
    private _tmp_edges_with_loss: Edge[] = []
    private _tmp_edges_with_distance: Edge[] = []
    private _tmp_edges_with_loss_and_distance: Edge[] = []
    private _graph: Network;

    /** list of log elements to be rendered to log body */
    private _logQueue: HTMLElement[];

    /** set of vertex ids scheduled for flashing */
    private _flashQueue: Set<string>;
    /** set of vertex ids scheduled for un-flash */
    private _flashingNodes: Set<string>;
    
    private _logPrinter: number;
    private _flasher: number;

    private _macMapping: { [mac: string]: string };

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

    /** from vertex for conn test */
    private _connFromNode: Vertex;

    /** from vertex id for conn test */
    // private _connFromNodeId: string;

    /** to vertex for conn test */
    private _connToNode: Vertex;

    /** to vertex id for conn test */
    // private _connToNodeId: string;

    

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

    /**
     * Build a new map UI controller.
     * 
     * @param config element bindings.
     */
    constructor(config: MapUiConfiguration) {
        this._datasource = config.datasource;
        this._mapElement = document.getElementById(config.mapElementId);
        this._infoPlateElement = document.getElementById(config.infoPlateElementId);
        this._connPlateElement = document.getElementById(config.connPlateElementId);
        
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

        this._resetMoveButton = document.getElementById(config.movementControls.resetButtonElementId) as HTMLButtonElement;
        this._moveForwardButton = document.getElementById(config.movementControls.forwardButtonElementId) as HTMLButtonElement;
        this._moveBackwardButton = document.getElementById(config.movementControls.backwardButtonElementId) as HTMLButtonElement;
        this._movementStatusText = document.getElementById(config.movementControls.statusElementId);

        this._connFromText = document.getElementById(config.connControls.connFromElementId);
        this._connToText = document.getElementById(config.connControls.connToElementId);
        this._connDistanceText = document.getElementById(config.connControls.connDistElementId);
        this._connLossText = document.getElementById(config.connControls.connLossElementId);
        this._connResultText = document.getElementById(config.connControls.connResultElementId);
        this._connTestButton = document.getElementById(config.connControls.connTestButtonElementId) as HTMLButtonElement;
        this._showLossCheckBox = document.getElementById(config.connControls.showLossCheckBoxElementId) as HTMLInputElement;
        this._showDistanceCheckBox = document.getElementById(config.connControls.showDistanceCheckBoxElementId) as HTMLInputElement;

        // this._filepathSubmitButton = document.getElementById(config.filePathControls.submitButtonElementId) as HTMLButtonElement;
        // this._filepathInput = document.getElementById(config.filePathControls.filePathInputElementId) as HTMLInputElement;
        // this._node_info_filepath = '';
        
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

        this._searchHighlightNodes = new Set<string>();

        this._macMapping = {};

        this._filterMode = 'filter';
        this._lastSearchTerm = '';

        this._windowManager = new WindowManager(config.windowManager.desktopElementId, config.windowManager.taskbarElementId);

        this._bpfCompletion = new Completion(bpfCompletionTree);

        this._resetMoveButton.onclick = async () => {
            this._movementStatusText.innerText = "0";
            this._updateMovement();
        };

        this._moveBackwardButton.onclick = async () => {
            let current_iter = parseFloat(this._movementStatusText.innerText) - 1;
            if(current_iter >= 0){
                this._movementStatusText.innerText = current_iter.toString();
                this._updateMovement();
            }
        }

        this._moveForwardButton.onclick = async () => {
            let current_iter = parseFloat(this._movementStatusText.innerText) + 1;
            if(current_iter < 30){
                this._movementStatusText.innerText = current_iter.toString();
                this._updateMovement();
            }
        }

        this._showLossCheckBox.onclick = () => {
            this._updateEdges();
        }

        this._showDistanceCheckBox.onclick = () => {
            this._updateEdges();
        }

        
        // this._connTestButton.onclick = () => {
        //     this._connResultText.innerText = ''
        //     let connToNode = this._connToNode.object as EmulatorNode;

        //     let connResultTitle = document.createElement('div');
        //     connResultTitle.className = 'title';
        //     connResultTitle.innerText = 'Connectivity Test Result';

        //     this._connResultText.appendChild(connResultTitle);
        //     console.log(connToNode.meta.emulatorInfo)
        //     if (connToNode.meta.emulatorInfo.routerid){
        //         let result = await this._datasource.startConnTest(connFromNode.Id, connToNode.meta.emulatorInfo.routerid)
        //         // let loss = result
        //         console.log(result.loss);
        //         console.log(result.routes);
        //         let routes = [];
        //         result.routes.split('\n').forEach(ip=>{
        //             routes.push(this._datasource.nodeIdByIp(ip));
        //         })
        //         if (this._edges){
        //             this._edges.clear();
        //         }
        //         this._tmp_edges = [];
        //         this._tmp_edges_with_distance = [];
        //         for (var i = 0; i < routes.length-1; i++) {
        //             console.log(routes[i])
        //             this._tmp_edges.push({
        //                 from: routes[i],
        //                 to: routes[i+1],
        //                 arrows: "to"
        //             });
        //             this._tmp_edges_with_distance.push({
        //                 from: routes[i],
        //                 to: routes[i+1],
        //                 arrows: "to",
        //                 label: "distance: "+this._getDistance(routes[i], routes[i+1]).toString()
        //             })
        //         }
        //         this._edges.update(this._tmp_edges_with_distance);
                  
        //         this._connResultText.appendChild(this._createInfoPlateValuePair('loss', result.loss))
        //         this._connResultText.appendChild(this._createInfoPlateValuePair('routes', '\n'+result.routes))
        //     }
        // }
        
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

        // this._filepathSubmitButton.onclick = () => {
        //     this._node_info_filepath = this._filepathInput.value;
        //     console.log(this._node_info_filepath);
        //     this.start();
        // }
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
                }
            });

            // at least one mac address matching a net is found, flash the node.
            // note: when no matching net is found, the "packet" may not be a
            // packet, but output from tcpdump.
            if (flashed.size > 0) {
                this._flashQueue.add(data.source);
            }

            let now = new Date();
            let lines: string[] = data.data.split('\r\n').filter(line => line !== '');

            if (lines.length > 0 && this._recording) {
                this._events.push({ lines: lines, source: data.source });
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
                id: n, borderWidth: 4
            });
        });

        unHighlighted.forEach(n => {
            updateRequest.push({
                id: n, borderWidth: 1
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

        if (this._filterMode == 'node-search') {
            // in node search mode, don't flash.
            this._flashingNodes.clear();
            return;
        }

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

    private async _focusNode(id: string) {
        this._graph.focus(id, { animation: true });
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
        span1.id = 'info_'+label;

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
            title.innerText = `${node.meta.emulatorInfo.role == 'Router' ? 'Router' : 'Host'}: ${vertex.label}`;

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

            if (node.meta.emulatorInfo.role == 'Router' || node.meta.emulatorInfo.role == 'Route Server') {
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

            // let connect = document.createElement('a');
            // let connect_input = document.createElement('input');
            // let connect_button = document.createElement('button');
            // let peer_node_id;
            // connect_button.innerText = 'Connect'
            // connect_button.onclick = async () => {
            //     let meta = node.meta.emulatorInfo;
            //     let node_name = `as${meta.asn}h-${meta.name}-${node.meta.emulatorInfo.nets[0].address.split("/")[0]}`;
            //     let peer_node_name = 'no';
            //     let distance = 0;
            //     this._nodes.forEach(node => {        
            //         if (node.type == 'node') {
            //             let nodeObj = (node.object as EmulatorNode);
            //             let nodeInfo = nodeObj.meta.emulatorInfo;
            //             if (nodeInfo.nets[0].address.split("/")[0] == connect_input.value){
            //                 peer_node_id = nodeObj.Id
            //                 peer_node_name = `as${nodeInfo.asn}h-${nodeInfo.name}-${nodeInfo.nets[0].address.split("/")[0]}`
            //                 distance = Math.abs(Number(nodeInfo.position_x) - Number(meta.position_x)) + Math.abs(Number(nodeInfo.position_y)-Number(meta.position_y))
            //             }                        
            //         }
            //     })
            //     this._tmp_edges.push({
            //         from: node.Id,
            //         to: peer_node_id,
            //         label: `${node.meta.emulatorInfo.nets[0].address.split("/")[0]}-${connect_input.value}`
            //     });
            //     await this._datasource.setMobileConnect(node_name, peer_node_name);
            //     await this._datasource.setTrafficControl(node.Id, connect_input.value, String(distance))
            //     this.redraw();
            //}
            // connect.append(connect_input);
            // connect.append(connect_button);

            actions.append(consoleLink);
            actions.append(netToggle);
            actions.append(reloadLink);
            // actions.append(connect);

            infoPlate.appendChild(actions);
        }

        this._infoPlateElement.innerText = '';
        this._infoPlateElement.appendChild(infoPlate);
        this._infoPlateElement.classList.remove('loading');
    }
    /**
     * update dist between given 2 nodes.
     */
    private async _updateDistance(){
        if(this._connFromNode && this._connToNode){
            const distance = this._getDistance(this._connFromNode.id, this._connToNode.id);            
            document.getElementById('info_Distance').innerText = distance.toString()+" m";
            console.log(distance.toString());
        }
    }
    /**
     * get dist between given 2 nodes.
     */
    private _getDistance(fromNodeId:string, toNodeId:string):number{
        let fromNode = this._nodes.get(fromNodeId)
        let toNode = this._nodes.get(toNodeId)
        const deltaX = fromNode.x - toNode.x;
        const deltaY = fromNode.y - toNode.y;
        const distance = parseFloat((Math.sqrt(deltaX ** 2 + deltaY ** 2)/10).toFixed(2));
        console.log(distance.toString());
        return distance
    }
    /**
     * get dist between given 2 nodes.
     */
    private _getLoss(fromNodeId:string, toNodeId:string):number{
        let vertex = this._nodes.get(fromNodeId).object as EmulatorNode;
        let fromId = parseInt(vertex.meta.emulatorInfo.routerid.split('.')[3])-100;

        vertex = this._nodes.get(toNodeId).object as EmulatorNode;
        let toId = parseInt(vertex.meta.emulatorInfo.routerid.split('.')[3])-100;
        console.log("fromId: "+fromId.toString() + "| toId: "+toId.toString());
        return this._datasource.getLoss(fromId.toString(), toId.toString());
    }

    /**
     * update edges with information to show
     */
    private _updateEdges(){
        this._edges.clear()
        if (this._showLossCheckBox.checked) {
            if (this._showDistanceCheckBox.checked){
                this._edges.update(this._tmp_edges_with_loss_and_distance);
            }else{
                this._edges.update(this._tmp_edges_with_loss);
            }
        }else if (this._showDistanceCheckBox.checked){
            this._edges.update(this._tmp_edges_with_distance);
        }else{
            this._edges.update(this._tmp_edges);
        }
    }

    /**
     * update infoplate with node.
     * 
     * @param nodeId node id for any vertex (can be node or net).
     */
    private async _updateConnectivityPlateWith(nodeId: string) {
        let vertex = this._nodes.get(nodeId);

        this._curretNode = vertex;
        if (this._connToNode && this._connFromNode){
            var prevFromNode = this._nodes.get(this._connFromNode.id)
            var prevToNode = this._nodes.get(this._connToNode.id)
            
            prevFromNode.color = null;
            prevToNode.color = null;

            this._nodes.update(prevFromNode);
            this._nodes.update(prevToNode);

            this._connToNode = vertex;
            vertex.color = "red";

            this._connFromNode = null;
        }else if (this._connToNode){
            this._connFromNode = vertex;
            vertex.color = "blue";

        }else{
            this._connToNode = vertex;
            vertex.color = "red";
        }

        this._nodes.update(vertex);
        if (this._edges){
            this._edges.clear();
        }

        let connToNode = this._connToNode.object as EmulatorNode;
        this._connToText.innerText = connToNode.meta.emulatorInfo.name;
        this._connFromText.innerText = "";

        if (this._connToNode && this._connFromNode){
            let connFromNode = this._connFromNode.object as EmulatorNode;
            this._connFromText.innerText = connFromNode.meta.emulatorInfo.name;
            
            this._updateDistanceAndLossBetweenSelectedNodes();

            this._connTestButton.innerText = 'Start Ping Test';
            this._connTestButton.onclick = async () => {
                this._connResultText.innerText = "";
                this._connResultText.classList.add('section');

                let connResultTitle = document.createElement('div');
                connResultTitle.className = 'title';
                connResultTitle.innerText = 'Connectivity Test Result';

                this._connResultText.appendChild(connResultTitle);
                console.log(connToNode.meta.emulatorInfo)
                if (connToNode.meta.emulatorInfo.routerid){
                    let result = await this._datasource.startConnTest(connFromNode.Id, connToNode.meta.emulatorInfo.routerid)
                    console.log(result.loss);
                    console.log(result.routes);
                    let routes = [];
                    result.routes.split('\n').forEach(ip=>{
                        routes.push(this._datasource.nodeIdByIp(ip));
                    })
                    if (this._edges){
                        this._edges.clear();
                    }
                    this._tmp_edges = [];
                    this._tmp_edges_with_distance = [];
                    this._tmp_edges_with_loss = [];
                    this._tmp_edges_with_loss_and_distance = [];
                    for (var i = 0; i < routes.length-1; i++) {
                        let loss_label = ""
                        let dist_label = ""
                        this._tmp_edges.push({
                            from: routes[i],
                            to: routes[i+1],
                            arrows: "to"
                        });
                        
                        if (routes[i]!=routes[i+1]){
                            dist_label = "distance: "+this._getDistance(routes[i], routes[i+1]).toString()
                            loss_label =  "loss: " + this._getLoss(routes[i], routes[i+1]).toString()
                        }
                        this._tmp_edges_with_distance.push({
                            from: routes[i],
                            to: routes[i+1],
                            arrows: "to",
                            label: dist_label
                        })
                        
                        this._tmp_edges_with_loss.push({
                            from: routes[i],
                            to: routes[i+1],
                            arrows: "to",
                            label: loss_label
                        })
                        this._tmp_edges_with_loss_and_distance.push({
                            from: routes[i],
                            to: routes[i+1],
                            arrows: "to",
                            label: dist_label + "\n" + loss_label
                        })
                    }
                    this._updateEdges();
                      
                    this._connResultText.appendChild(this._createInfoPlateValuePair('loss', result.loss))
                    this._connResultText.appendChild(this._createInfoPlateValuePair('routes', '\n'+result.routes))
                }
            }
        }

        if (this._connToNode && !this._connFromNode){
            this._updateDistanceAndLossBetweenSelectedNodes();
            this._connTestButton.innerText = 'Show Next Hop';
            this._connTestButton.onclick = async () => {
                this._connResultText.innerText = "";
                this._edges.clear();
                this._tmp_edges = [];
                this._tmp_edges_with_distance = [];
                this._tmp_edges_with_loss = [];
                this._tmp_edges_with_loss_and_distance = [];

                this._connResultText.classList.add('section');

                let connResultTitle = document.createElement('div');
                connResultTitle.className = 'title';
                connResultTitle.innerText = 'Connectivity Test Result';

                this._connResultText.appendChild(connResultTitle);
                
                this._nodes.forEach(async node=>{
                    let fromNode = node.object as EmulatorNode;
                    console.log(fromNode.meta.emulatorInfo.nets[0].address)
                    if (connToNode.meta.emulatorInfo.nets[0].address != fromNode.meta.emulatorInfo.nets[0].address){
                        let result = await this._datasource.showNextHop(fromNode.Id, connToNode.meta.emulatorInfo.routerid)
                        let dist_label = "";
                        let loss_label = "";
                        let from = node.id;
                        let to = this._datasource.nodeIdByIp(result.nextHop);

                        this._tmp_edges.push({
                            from: from,
                            to: to,
                            arrows: "to"
                        });

                        dist_label = "distance: "+this._getDistance(from, to).toString()
                        loss_label =  "loss: " + this._getLoss(from, to).toString()
                        
                        this._tmp_edges_with_distance.push({
                            from: from,
                            to: to,
                            arrows: "to",
                            label: dist_label

                        });

                        this._tmp_edges_with_loss.push({
                            from: from,
                            to: to,
                            arrows: "to",
                            label: loss_label

                        });

                        this._tmp_edges_with_loss_and_distance.push({
                            from: from,
                            to: to,
                            arrows: "to",
                            label: dist_label + "\n" + loss_label
                        });

                    }
                    this._updateEdges();
                })
                
            }
        }

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
            });
        });
    }

    private async _updateMovement() {
        let current_iter =  this._movementStatusText.innerText;
        await this._datasource.moveNodePosition(current_iter);
        this._nodes.forEach(async node=>{
            await this._datasource.moveNodeContainer(node.id, current_iter)
        })
    }

    private _updateDistanceAndLossBetweenSelectedNodes(){
        if (this._connToNode && this._connFromNode){
            this._connToNode = this._nodes.get(this._connToNode.id);
            this._connFromNode = this._nodes.get(this._connFromNode.id);

            let distance = this._getDistance(this._connFromNode.id, this._connToNode.id);
            this._connDistanceText.innerText = distance.toString()+"m"
            let loss = this._getLoss(this._connFromNode.id, this._connToNode.id);
            this._connLossText.innerText = loss.toString()+"%"
        } else {
            this._connDistanceText.innerText = "- m";
            this._connLossText.innerText = "- %"
        }
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
                id: nodeId, borderWidth: 1
            }
        });
        this._nodes.update(unflashRequest);
        this._flashingNodes.clear();
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

    private _buildPlayList() : PlaylistItem[] {
        let refDate = new Date();

        let playlist: PlaylistItem[] = [];

        this._events.forEach(e => {
            e.lines.forEach(line => {
                let time = line.split(' ')[0];
                let [ h, m, _s ] = time.split(':');
                
                if (!h || !m || !_s) {
                    return;
                }

                let [ s, ms ] = _s.split('.');

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

                playlist.push({ nodes: nodes, at: date.valueOf() });
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
            return {
                id: nodeId, borderWidth: 1
            }
        });
        this._nodes.update(unflashRequest);
        this._flashingNodes.clear();
    
        // flash nodes from this event.
        let current = this._playlist[this._replayPos];
        current.nodes.forEach(node => this._flashingNodes.add(node));
        let flashRequest = Array.from(this._flashingNodes).map(nodeId => {
            return {
                id: nodeId, borderWidth: 4
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
        // if(this._node_info_filepath != ''){
        await this._datasource.get_position();
        this.redraw();
       
        this._mapMacAddresses();

        if (this._filterMode == 'filter') {
            this._filterInput.value = await this._datasource.getSniffFilter();
        }
        window.setInterval(async () => {
            await this.movement();
        }, 500);

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

    /**
     * disconnect datasource and stop log/flash worker.
     */
    stop() {
        this._datasource.disconnect();
        window.clearInterval(this._logPrinter);
        window.clearInterval(this._flasher);
    }

    async movement() {
        // if(this._node_info_filepath == ''){
        //     return
        // }
        await this._datasource.get_position();

        var updated_nodes = this._datasource.vertices;
        var is_moved = false;
        this._movementStatusText.innerText = this._datasource.iter.toString();

        new DataSet(updated_nodes).forEach(node=>{
            if (node.x != this._nodes.get(node.id).x){
                is_moved = true;
                return
            }
            if (node.y != this._nodes.get(node.id).y){
                is_moved = true;
                return
            }
        })
        
        if (is_moved){
            this._edges.clear()
            console.log("moved")
            this._updateDistance()
            this._nodes.clear()
            // remove
            //this._edges.update(updated_edges);
            updated_nodes.forEach(node=>{
                if (this._connFromNode && node.id==this._connFromNode.id){
                    node.color = 'blue';
                }
                if (this._connToNode && node.id==this._connToNode.id){
                    node.color = 'red';
                }
            })
            this._nodes.update(updated_nodes);
            this._updateDistanceAndLossBetweenSelectedNodes()

        }
        
    }
    /**
     * redraw map.
     */
    redraw() {
        //remove edges
        this._edges = new DataSet();
        this._nodes = new DataSet(this._datasource.vertices);
        this._buildings = new DataSet(this._datasource.buildings);

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
            groups,
            physics:{
                stabilization: true
            }
        });

        this._graph.moveTo({
            position: {x: 0, y: 0},
            offset: {x: -1000/2, y: -1000/2},
            scale: 0.5,
        });

        // draw grid
        this._graph.on("beforeDrawing", (ctx) => {

            var width = 1000;
            var height = 1000;
            var spacing = 50;
            var gridExtentFactor = 10;
            ctx.strokeStyle = "lightblue";
            
            // draw grid
            ctx.beginPath();
            for (var x = -width * gridExtentFactor; x <= width * gridExtentFactor; x += spacing) {
              ctx.moveTo(x, height * gridExtentFactor);
              ctx.lineTo(x, -height * gridExtentFactor);
            }
            for (var y = -height * gridExtentFactor; y <= height * gridExtentFactor; y += spacing) {
              ctx.moveTo(width * gridExtentFactor, y);
              ctx.lineTo(-width * gridExtentFactor, y);
            }
            ctx.stroke();

            // Draw buildings
            this._buildings.forEach(function (building) {
                if (building.type === 'building') {
            
                  // Define the rectangle properties
                  var width = building.width; // Width of the rectangle
                  var height = building.height; // Height of the rectangle
                  var x = building.x; // X-coordinate of the top-left corner
                  var y = building.y; // Y-coordinate of the top-left corner
            
                  // Set the rectangle style
                  ctx.fillStyle = 'lightgrey'; // Fill color
                  ctx.fillRect(x, y, width, height); // Draw the rectangle
                }
              });
        });
        
        this._graph.on('click', (ev) => {
            this._suggestions.innerText = '';
            this._moveSuggestionSelection('clear');
            
            if (ev.nodes.length <= 0) {
                return;
            }
            let vertex = this._nodes.get(ev.nodes[0]);
            console.log(vertex)
            this._updateInfoPlateWith(ev.nodes[0]);
            this._updateConnectivityPlateWith(ev.nodes[0]);            
        });

        // this._graph.on("afterDrawing", (ctx) => {

        //     // this._nodes = new DataSet(this._datasource.vertices);
            
        // });

    }
}
