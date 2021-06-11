import './css/map.css';
import '../common/css/window-manager.css';
import 'bootstrap/dist/css/bootstrap.min.css';

import { DataSource } from './datasource';
import { MapUi } from './ui';
import { Configuration } from '../common/configuration';

const datasource = new DataSource(Configuration.ApiPath);
const mapUi = new MapUi({
    datasource,
    mapElementId: 'map',
    infoPlateElementId: 'info-plate',
    filterInputElementId: 'filter',
    filterWrapElementId: 'filter-wrap',
    logPanelElementId: 'log-panel',
    logBodyElementId: 'log-body',
    logViewportElementId: 'log-viewport',
    logControls: {
        autoscrollCheckboxElementId: 'log-autoscroll',
        clearButtonElementId: 'log-clear',
        disableCheckboxElementId: 'log-disable'
    },
    filterControls: {
        filterModeTabElementId: 'tab-filter-mode',
        nodeSearchModeTabElementId: 'tab-node-search-mode',
        suggestionsElementId: 'filter-suggestions'
    },
    windowManager: {
        desktopElementId: 'console-area',
        taskbarElementId: 'taskbar'
    }
});

mapUi.start();