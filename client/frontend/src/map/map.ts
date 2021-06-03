import './css/map.css';
import { DataSource } from './datasource';
import { MapUi } from './ui';

const API_PATH = '/api/v1';

const datasource = new DataSource(API_PATH);
const mapUi = new MapUi({
    datasource,
    mapElementId: 'map',
    infoPlateElementId: 'info-plate',
    filterInputElementId: 'filter',
    filterWrapElementId: 'filter-wrap',
    logBodyElementId: 'log-body',
    logViewportElementId: 'log-viewport',
    logControls: {
        autoscrollCheckboxElementId: 'log-autoscroll',
        clearButtonElementId: 'log-clear',
        disableCheckboxElementId: 'log-disable'
    }
});

mapUi.start();