import './css/index.css';
import '../common/css/window-manager.css';
import 'bootstrap/dist/css/bootstrap.min.css';
import 'datatables.net-bs4/css/dataTables.bootstrap4.min.css'
import 'datatables.net-select-bs4/css/select.bootstrap4.min.css'

import 'bootstrap';
import 'datatables.net';
import 'datatables.net-bs4';
import 'datatables.net-select';
import 'datatables.net-select-bs4';

import {IndexUi} from './ui';

var ui = new IndexUi({
    installListElementId: 'install-list',
    desktopElementId: 'console-area',
    taskbarElementId: 'taskbar'
});

ui.loadInstalls('/api/v1/install');
ui.loadUninstalls('/api/v1/uninstall');