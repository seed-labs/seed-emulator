import { DataSet } from 'vis-data';
import { Network } from 'vis-network';
import { EmulatorNetwork, EmulatorNode } from '../common/types';
import { WindowManager } from '../common/window-manager';
import { DataSource, Edge, Vertex } from './datasource';

export interface MapUiConfiguration {
    datasource: DataSource,
    mapElementId: string,
    infoPlateElementId: string,
    filterInputElementId: string,
    filterWrapElementId: string,
    logBodyElementId: string,
    logPanelElementId: string,
    logViewportElementId: string,
    logControls: {
        clearButtonElementId: string,
        autoscrollCheckboxElementId: string,
        disableCheckboxElementId: string
    },
    filterControls: {
        filterModeTabElementId: string,
        nodeSearchModeTabElementId: string
    },
    windowManager: {
        desktopElementId: string,
        taskbarElementId: string
    }
}

type FilterMode = 'node-search' | 'filter';

export class MapUi {
    private _mapElement: HTMLElement;
    private _infoPlateElement: HTMLElement;
    private _filterInput: HTMLInputElement;
    private _filterWrap: HTMLElement;

    private _logPanel: HTMLElement;
    private _logView: HTMLElement;
    private _logBody: HTMLElement;
    private _logAutoscroll: HTMLInputElement;
    private _logDisable: HTMLInputElement;
    private _logClear: HTMLElement;

    private _filterModeTab: HTMLElement;
    private _searchModeTab: HTMLElement;

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

    private _filterMode: FilterMode;
    private _searchHighlightNodes: Set<string>;
    private _lastSearchTerm: string;

    private _windowManager: WindowManager;

    constructor(config: MapUiConfiguration) {
        this._datasource = config.datasource;
        this._mapElement = document.getElementById(config.mapElementId);
        this._infoPlateElement = document.getElementById(config.infoPlateElementId);
        this._filterInput = document.getElementById(config.filterInputElementId) as HTMLInputElement;
        this._filterWrap = document.getElementById(config.filterWrapElementId);

        this._logPanel = document.getElementById(config.logPanelElementId);
        this._logView = document.getElementById(config.logViewportElementId);
        this._logBody = document.getElementById(config.logBodyElementId);
        this._logAutoscroll = document.getElementById(config.logControls.autoscrollCheckboxElementId) as HTMLInputElement;
        this._logDisable = document.getElementById(config.logControls.disableCheckboxElementId) as HTMLInputElement;
        this._logClear = document.getElementById(config.logControls.clearButtonElementId);

        this._filterModeTab = document.getElementById(config.filterControls.filterModeTabElementId);
        this._searchModeTab = document.getElementById(config.filterControls.nodeSearchModeTabElementId);

        this._freezed = false;

        this._logQueue = [];

        this._flashQueue = new Set<string>();
        this._flashingNodes = new Set<string>();

        this._searchHighlightNodes = new Set<string>();

        this._macMapping = {};

        this._filterMode = 'filter';
        this._lastSearchTerm = '';

        this._windowManager = new WindowManager(config.windowManager.desktopElementId, config.windowManager.taskbarElementId);

        this._searchModeTab.onclick = () => {
            this._setFilterMode('node-search');
        };

        this._filterModeTab.onclick = () => {
            this._setFilterMode('filter');
        };

        this._logClear.onclick = () => {
            this._logBody.innerText = '';
        };

        this._windowManager.on('taskbarchanges', (shown: boolean) => {
            if (shown) {
                this._logPanel.classList.add('bump');
            } else {
                this._logPanel.classList.remove('bump');
            }
        });

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

    private _flashNodes() {
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

    private async _setFilterMode(mode: FilterMode) {
        if (mode == this._filterMode) {
            return;
        }

        this._filterMode = mode;

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

    private async _filterUpdateHandler(event: KeyboardEvent, forced: boolean = false) {
        if ((!event || event.key != 'Enter') && !forced) {
            return;
        }

        let term = this._filterInput.value;

        if (this._filterMode == 'filter') {
            this._blocked = true;
            this._freeze();
            this._filterInput.value = await this._datasource.setSniffFilter(term);
            this._blocked = false;
        }

        if (this._filterMode == 'node-search') {
            var hits = new Set<string>();
            this._lastSearchTerm = term;

            this._nodes.forEach(node => {
                var targetString = '';

                if (node.type == 'node') {
                    let nodeObj = (node.object as EmulatorNode);
                    let nodeInfo = nodeObj.meta.emulatorInfo;

                    targetString = `${nodeObj.Id} ${nodeInfo.role} as${nodeInfo.asn} ${nodeInfo.name} `;

                    nodeInfo.nets.forEach(net => {
                        targetString += `${net.name} ${net.address} `;
                    });
                }

                if (node.type == 'network') {
                    let net = (node.object as EmulatorNetwork);
                    let netInfo = net.meta.emulatorInfo;

                    targetString = `${net.Id} as${netInfo.scope} ${netInfo.name} ${netInfo.prefix}`;
                }

                if (term != '' && targetString.toLowerCase().includes(term.toLowerCase())) {
                    hits.add(node.id);
                }
            });

            this._updateSearchHighlights(hits);
        }
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

    private async _updateInfoPlateWith(nodeId: string) {
        let vertex = this._nodes.get(nodeId);

        let infoPlate = document.createElement('div');
        this._infoPlateElement.classList.add('loading');

        let title = document.createElement('div');
        title.className = 'title';
        infoPlate.appendChild(title);

        if (vertex.type == 'network') {
            let net = vertex.object as EmulatorNetwork;
            title.innerText = `${net.meta.emulatorInfo.type == 'global' ? 'Exchange' : 'Network'}: ${vertex.label}`;

            infoPlate.appendChild(this._createInfoPlateValuePair('ID', net.Id.substr(0, 12)));
            infoPlate.appendChild(this._createInfoPlateValuePair('Name', net.meta.emulatorInfo.name));
            infoPlate.appendChild(this._createInfoPlateValuePair('Scope', net.meta.emulatorInfo.scope));
            infoPlate.appendChild(this._createInfoPlateValuePair('Type', net.meta.emulatorInfo.type));
            infoPlate.appendChild(this._createInfoPlateValuePair('Prefix', net.meta.emulatorInfo.prefix));
        }

        if (vertex.type == 'node') {
            let node = vertex.object as EmulatorNode;
            title.innerText = `${node.meta.emulatorInfo.role == 'Router' ? 'Router' : 'Host'}: ${vertex.label}`;

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

            actions.append(consoleLink);
            actions.append(netToggle);
            actions.append(reloadLink);

            infoPlate.appendChild(actions);
        }

        this._infoPlateElement.innerText = '';
        this._infoPlateElement.appendChild(infoPlate);
        this._infoPlateElement.classList.remove('loading');
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

        if (this._filterMode == 'filter') {
            this._filterInput.value = await this._datasource.getSniffFilter();
        }

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