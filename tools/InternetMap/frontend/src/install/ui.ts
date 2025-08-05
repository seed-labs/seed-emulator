import $ from 'jquery';
import {InstallType} from '../common/types';
import {WindowManager} from '../common/window-manager';
import {ApiRespond} from "../map2/datasource";

export class IndexUi {
    private _installTable: DataTables.Api;
    private _wm: WindowManager;
    private _installToolbar: HTMLDivElement;
    private _installUrl: string;
    private _uninstallUrl: string;

    constructor(config: {
        installListElementId: string,
        desktopElementId: string,
        taskbarElementId: string
    }) {
        this._installTable = $(`#${config.installListElementId}`).DataTable({
            columnDefs: [
                {
                    targets: [2],
                    orderable: false
                },
                {
                    targets: 0,
                    className: 'select-checkbox',
                    orderable: false
                }
            ],
            select: {
                selector: 'td:first-child',
                style: 'multi'
            },
            order: [[1, 'asc']],
            dom:
                "<'row'<'col-9 toolbar install-toolbar'><'col-3'f>>" +
                "<'row'<'col-12'tr>>" +
                "<'row'<'col-12'i>>" +
                "<'row'<'col-12'p>>"

        });

        this._installToolbar = document.querySelector('.install-toolbar');
        this._wm = new WindowManager(config.desktopElementId, config.taskbarElementId);

        this._configureToolbar(this._installTable, this._installToolbar);

        this._initInstallToolbar()
    }

    private _initInstallToolbar() {
        var btnGroupSelectedOptions = document.createElement('div');
        btnGroupSelectedOptions.className = 'btn-group mr-1 mb-1';

        btnGroupSelectedOptions.appendChild(this._createBtn(
            'Attach selected',
            'btn btn-sm btn-primary',
            () => {
                var console = this._wm.createWindow.bind(this._wm);
                this._installTable.rows({
                    selected: true,
                    search: 'applied'
                }).nodes().each((row: HTMLTableRowElement) => {
                    console(row.id, row.title);
                });
            }
        ));

        btnGroupSelectedOptions.appendChild(this._createBtn(
            'Run on selected…',
            'btn btn-sm btn-info',
            () => alert('Not implemented')
        ));

        btnGroupSelectedOptions.appendChild(this._createBtn(
            'Kill selected…',
            'btn btn-sm btn-danger',
            () => alert('Not implemented')
        ));

        this._installToolbar.appendChild(btnGroupSelectedOptions);

        // this._installToolbar.appendChild(this._createBtn(
        //     'Add Install…',
        //     'btn btn-sm btn-success mr-1 mb-1',
        //     () => alert('Not implemented'),
        //     'bi bi-plus mr-1'
        // ));

        this._installToolbar.appendChild(this._createBtn(
            'Reload',
            'btn btn-sm btn-light mr-1 mb-1',
            this._reloadInstalls.bind(this),
            'bi bi-arrow-clockwise'
        ));
    }

    private _reloadInstalls() {
        if (!this._installUrl) return;

        this.loadInstalls(this._installUrl);
    }

    private _createBtn(text: string, className: string, cb: any, iconClassName?: string): HTMLButtonElement {
        var btn = document.createElement('button');
        var btnIcon = document.createElement('i');
        var btnText = document.createElement('span');

        btnText.innerText = text;

        btn.className = className;
        if (iconClassName) {
            btnIcon.className = iconClassName;
            btn.appendChild(btnIcon);
        }
        btn.appendChild(btnText);
        btn.onclick = cb;

        return btn;
    }

    private _configureToolbar(table: DataTables.Api, toolbar: HTMLDivElement) {
        var btnGroupSelects = document.createElement('div');
        btnGroupSelects.className = 'btn-group mr-1 mb-1';

        btnGroupSelects.appendChild(this._createBtn(
            'Select All',
            'btn btn-sm btn-secondary',
            () => table.rows({search: 'applied'}).select()
        ));

        btnGroupSelects.appendChild(this._createBtn(
            'Invert Selections',
            'btn btn-sm btn-info',
            () => {
                var selected = table.rows({selected: true, search: 'applied'});
                var rest = table.rows({selected: false, search: 'applied'});

                rest.select();
                selected.deselect();
            }
        ));

        btnGroupSelects.appendChild(this._createBtn(
            'Deselect All',
            'btn btn-sm btn-light',
            () => table.rows({search: 'applied'}).deselect()
        ));

        toolbar.appendChild(btnGroupSelects);
    }

    private _createInstallRow(installObj: InstallType) {
        var obj = installObj.meta.baseInfo;

        var tr = document.createElement('tr');

        var tds = document.createElement('td');
        var td1 = document.createElement('td');
        var td4 = document.createElement('td');

        td1.className = 'text-monospace';

        td1.innerText = obj.name;

        var console = this._wm.createWindow.bind(this._wm);
        var id = installObj.Id.substr(0, 12);
        var title = `install ${obj.name}`;
        let _loadV2 = this._loadV2
        let _installUrl = this._installUrl
        let _uninstallUrl = this._uninstallUrl

        td4.appendChild(this._createBtn(
            'Install',
            'btn btn-sm btn-primary mr-1 mb-1',
            async () => {
                let ret = await _loadV2('POST', _installUrl, JSON.stringify({id: id, title: title}))
                alert(ret.result);
                return
            }
        ));

        td4.appendChild(this._createBtn(
            'Uninstall',
            'btn btn-sm btn-danger mr-1 mb-1',
            async () => {
                let ret = await _loadV2('POST', _uninstallUrl, JSON.stringify({id: id, title: title}))
                alert(ret.result);
                return
            }
        ));

        [tds, td1, td4].forEach(td => tr.appendChild(td));

        tr.id = id;
        tr.title = title;

        return tr;
    }

    private _load(url: string, table: DataTables.Api, handler: (data: any) => HTMLTableRowElement) {
        var xhr = new XMLHttpRequest();
        var createRow = handler.bind(this);

        table.clear();

        xhr.open('GET', url);
        xhr.onload = function () {
            if (xhr.status == 200) {
                var res = JSON.parse(xhr.responseText);
                if (!res.ok) return;

                res.result.forEach((c) => {
                    table.row.add(createRow(c));
                });
            }
            table.draw();
        };

        xhr.send();
    }

    private async _loadV2<ResultType>(method: string, url: string, body: string = undefined): Promise<ApiRespond<ResultType>> {
        let xhr = new XMLHttpRequest();

        xhr.open(method, url);

        if (method == 'POST') {
            xhr.setRequestHeader('Content-Type', 'application/json;charset=UTF-8');
        }

        return new Promise((resolve, reject) => {
            xhr.onload = function () {
                if (this.status != 200) {
                    reject({
                        ok: false,
                        result: 'non-200 response from API.'
                    });

                    return;
                }

                var res = JSON.parse(xhr.response);

                if (res.ok) {
                    resolve(res);
                } else {
                    reject(res);
                }
            };

            xhr.onerror = function () {
                reject({
                    ok: false,
                    result: 'xhr failed.'
                });
            }

            xhr.send(body);
        })
    }

    loadInstalls(url: string) {
        this._installUrl = url;
        this._load(url, this._installTable, this._createInstallRow);
    }

    loadUninstalls(url: string) {
        this._uninstallUrl = url;
    }
}