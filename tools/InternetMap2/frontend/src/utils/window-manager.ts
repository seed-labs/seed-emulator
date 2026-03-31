import {type ConsoleEvent} from './console-event';
import type {IframeQueryData} from "@/types";

export type WindowManagerEvent = 'taskbarchanges';

/**
 * Console window using pure DOM with drag/resize functionality
 */
export class Window {
    private _id: string;
    private _title: string;
    private _statusText: string;
    private _element: HTMLDivElement;
    private _titleElement: HTMLSpanElement;
    private _frameElement: HTMLIFrameElement;
    private _manager: WindowManager;
    private _maskElement: HTMLDivElement;
    private _titleBarElement: HTMLDivElement;
    private _contentElement: HTMLDivElement;
    private _x: number;
    private _y: number;
    private _dx: number;
    private _dy: number;
    private _dragging: boolean;
    private _inSynth: boolean;
    private _synthControlElement: HTMLElement;
    private _isResizing: boolean = false;
    private _resizeDirection: string | null = null;

    private _initialWidth: number;
    private _initialHeight: number;
    private _initialX: number;
    private _initialY: number;
    private _isMinimized: boolean = false;
    private _isFocused: boolean = false;

    // Event handlers
    private _mousedownHandler: (e: MouseEvent) => void;
    private _mouseupHandler: (e: MouseEvent) => void;
    private _mousemoveHandler: (e: MouseEvent) => void;

    constructor(manager: WindowManager, id: string, title: string, url: string, top: number, left: number) {
        this._manager = manager;
        this._dragging = false;
        this._inSynth = false;
        this._id = id;
        this._title = title;
        this._statusText = '(connecting...)';
        this._isMinimized = false;
        this._isFocused = false;

        this._initialWidth = 800;
        this._initialHeight = 600;
        this._initialX = left;
        this._initialY = top;

        this._frameElement = this._createIframe(url);

        this._createWindowElement();
        this._setupEventListeners();
    }

    private _createWindowElement(): void {
        const windowEl = document.createElement('div');
        windowEl.className = 'console-window';
        windowEl.style.position = 'absolute';
        windowEl.style.left = `${this._initialX}px`;
        windowEl.style.top = `${this._initialY}px`;
        windowEl.style.width = `${this._initialWidth}px`;
        windowEl.style.height = `${this._initialHeight}px`;
        windowEl.style.zIndex = '10000';
        windowEl.style.border = '1px solid #dcdfe6';
        windowEl.style.background = '#ffffff';
        windowEl.style.borderRadius = '4px';
        windowEl.style.boxShadow = '0 2px 12px 0 rgba(0, 0, 0, 0.1)';
        windowEl.style.overflow = 'hidden';
        windowEl.style.display = 'flex';
        windowEl.style.flexDirection = 'column';
        windowEl.style.userSelect = 'none';

        const titleBar = document.createElement('div');
        titleBar.className = 'console-titlebar';
        titleBar.style.padding = '12px 16px';
        titleBar.style.background = '#f5f7fa';
        titleBar.style.borderBottom = '1px solid #ebeef5';
        titleBar.style.cursor = 'move';
        titleBar.style.display = 'flex';
        titleBar.style.justifyContent = 'space-between';
        titleBar.style.alignItems = 'center';
        titleBar.style.userSelect = 'none';
        titleBar.style.fontSize = '14px';
        titleBar.style.fontWeight = '500';

        const titleText = document.createElement('span');
        titleText.className = 'console-title';
        titleText.innerText = `${this._title} ${this._statusText}`;
        titleText.style.flexGrow = '1';
        titleText.style.overflow = 'hidden';
        titleText.style.textOverflow = 'ellipsis';
        titleText.style.whiteSpace = 'nowrap';

        const titleActions = document.createElement('div');
        titleActions.className = 'console-actions';
        titleActions.style.display = 'flex';
        titleActions.style.gap = '8px';
        titleActions.style.alignItems = 'center';

        const buttons = [
            {
                icon: '⌨️',
                title: 'Add this session to input broadcast',
                action: () => this.toggleSynth(),
                ref: '_synthControlElement',
                className: 'synth-control'
            },
            {
                icon: '↻',
                title: 'Reload terminal',
                action: () => this.reload(),
                className: 'reload-control'
            },
            {
                icon: '↗',
                title: 'Open in new window',
                action: () => this.popOut(),
                className: 'popout-control'
            },
            {
                icon: '🗕',
                title: 'Minimize',
                action: () => this.minimize(),
                className: 'minimize-control'
            },
            {
                icon: '✕',
                title: 'Close',
                action: () => this.close(),
                className: 'close-control'
            }
        ];

        buttons.forEach(btn => {
            const button = document.createElement('button');
            button.innerHTML = btn.icon;
            button.title = btn.title;
            button.className = `console-action ${btn.className}`;
            button.style.background = 'none';
            button.style.border = 'none';
            button.style.cursor = 'pointer';
            button.style.fontSize = '14px';
            button.style.padding = '4px';
            button.style.borderRadius = '3px';
            button.style.transition = 'background-color 0.2s';
            button.onclick = (e) => {
                e.stopPropagation();
                btn.action();
            };

            button.onmouseenter = () => {
                button.style.backgroundColor = '#f0f0f0';
            };

            button.onmouseleave = () => {
                button.style.backgroundColor = 'transparent';
            };

            if (btn.ref) {
                (this as any)[btn.ref] = button;
            }

            titleActions.appendChild(button);
        });

        const contentArea = document.createElement('div');
        contentArea.className = 'console-content';
        contentArea.style.flexGrow = '1';
        contentArea.style.position = 'relative';
        contentArea.style.overflow = 'hidden';

        const mask = document.createElement('div');
        mask.className = 'console-mask hide';
        mask.style.position = 'absolute';
        mask.style.top = '0';
        mask.style.left = '0';
        mask.style.width = '100%';
        mask.style.height = '100%';
        mask.style.zIndex = '10';
        mask.style.display = 'none';

        titleBar.appendChild(titleText);
        titleBar.appendChild(titleActions);

        contentArea.appendChild(this._frameElement);
        contentArea.appendChild(mask);

        windowEl.appendChild(titleBar);
        windowEl.appendChild(contentArea);

        this._createResizeHandles(windowEl);

        this._element = windowEl;
        this._titleBarElement = titleBar;
        this._titleElement = titleText;
        this._contentElement = contentArea;
        this._maskElement = mask;
    }

    private _createResizeHandles(container: HTMLDivElement): void {
        const directions = ['n', 'ne', 'e', 'se', 's', 'sw', 'w', 'nw'];

        directions.forEach(dir => {
            const handle = document.createElement('div');
            handle.className = `resize-handle resize-${dir}`;
            handle.style.position = 'absolute';
            handle.style.zIndex = '1000';
            handle.style.pointerEvents = 'auto';

            switch (dir) {
                case 'n':
                    handle.style.top = '0';
                    handle.style.left = '0';
                    handle.style.right = '0';
                    handle.style.height = '4px';
                    handle.style.cursor = 'ns-resize';
                    break;
                case 'ne':
                    handle.style.top = '0';
                    handle.style.right = '0';
                    handle.style.width = '10px';
                    handle.style.height = '10px';
                    handle.style.cursor = 'nesw-resize';
                    break;
                case 'e':
                    handle.style.top = '0';
                    handle.style.right = '0';
                    handle.style.bottom = '0';
                    handle.style.width = '4px';
                    handle.style.cursor = 'ew-resize';
                    break;
                case 'se':
                    handle.style.bottom = '0';
                    handle.style.right = '0';
                    handle.style.width = '10px';
                    handle.style.height = '10px';
                    handle.style.cursor = 'nwse-resize';
                    break;
                case 's':
                    handle.style.bottom = '0';
                    handle.style.left = '0';
                    handle.style.right = '0';
                    handle.style.height = '4px';
                    handle.style.cursor = 'ns-resize';
                    break;
                case 'sw':
                    handle.style.bottom = '0';
                    handle.style.left = '0';
                    handle.style.width = '10px';
                    handle.style.height = '10px';
                    handle.style.cursor = 'nesw-resize';
                    break;
                case 'w':
                    handle.style.top = '0';
                    handle.style.left = '0';
                    handle.style.bottom = '0';
                    handle.style.width = '4px';
                    handle.style.cursor = 'ew-resize';
                    break;
                case 'nw':
                    handle.style.top = '0';
                    handle.style.left = '0';
                    handle.style.width = '10px';
                    handle.style.height = '10px';
                    handle.style.cursor = 'nwse-resize';
                    break;
            }

            handle.onmousedown = (e) => {
                e.stopPropagation();
                this._startResize(e, dir);
            };

            container.appendChild(handle);
        });
    }

    private _createIframe(url: string): HTMLIFrameElement {
        const frameElement = document.createElement('iframe');
        frameElement.src = url;
        frameElement.className = 'console-iframe';
        frameElement.setAttribute('container-id', this._id);
        frameElement.style.width = '100%';
        frameElement.style.height = '100%';
        frameElement.style.border = 'none';
        frameElement.style.display = 'block';
        frameElement.setAttribute('allow', 'clipboard-read; clipboard-write');
        frameElement.setAttribute('sandbox', 'allow-same-origin allow-scripts allow-forms allow-popups allow-modals');

        frameElement.onload = () => {
            this.setStatusText('');
            try {
                if (frameElement.contentWindow) {
                    const style = document.createElement('style');
                    style.textContent = `
            body, html {
              margin: 0;
              padding: 0;
              height: 100%;
              width: 100%;
              overflow: hidden;
            }
          `;

                    if (frameElement.contentDocument) {
                        frameElement.contentDocument.head.appendChild(style);
                        frameElement.contentDocument.body.style.width = '100%';
                        frameElement.contentDocument.body.style.height = '100%';
                        frameElement.contentDocument.body.style.margin = '0';
                        frameElement.contentDocument.body.style.padding = '0';
                        frameElement.contentDocument.body.style.overflow = 'hidden';
                    }
                }
            } catch (e) {
                console.log('Cannot access iframe content due to cross-origin restrictions');
            }
        };

        frameElement.onerror = () => {
            this.setStatusText('(error loading)');
        };

        return frameElement;
    }

    private _setupEventListeners(): void {
        this._mousedownHandler = this._handleDragStart.bind(this);
        this._mouseupHandler = this._handleDragEnd.bind(this);
        this._mousemoveHandler = this._handleDragMove.bind(this);

        this._titleBarElement.addEventListener('mousedown', this._mousedownHandler);
        document.addEventListener('mouseup', this._mouseupHandler);

        this._element.addEventListener('click', (e) => {
            const target = e.target as HTMLElement;

            if (target === this._element || target === this._titleBarElement ||
                this._titleBarElement.contains(target)) {
                this._manager.setActiveWindowDirect(this);
            }
        });

        this._frameElement.addEventListener('load', () => {
            this._attachIframeEvents();
        });
    }

    private _attachIframeEvents(): void {
        if (this._frameElement.contentWindow) {
            try {
                const contentDocument = this._frameElement.contentDocument;
                if (contentDocument) {
                    contentDocument.addEventListener('click', (e) => {
                        this._manager.setActiveWindowDirect(this);
                    });

                    contentDocument.addEventListener('mousedown', (e) => {
                        this._manager.setActiveWindowDirect(this);
                    });
                }
            } catch (e) {
                console.log(`Cannot access iframe content due to cross-origin restrictions: ${e}`)
            }
        }
    }

    private _startResize(e: MouseEvent, direction: string): void {
        e.preventDefault();
        e.stopPropagation();

        this._manager.setActiveWindowDirect(this);
        this._isResizing = true;
        this._resizeDirection = direction;
        this._initialX = e.clientX;
        this._initialY = e.clientY;
        this._initialWidth = this._element.offsetWidth;
        this._initialHeight = this._element.offsetHeight;

        const rect = this._element.getBoundingClientRect();
        const startX = rect.left;
        const startY = rect.top;

        const mouseMoveHandler = (e: MouseEvent) => {
            if (!this._isResizing) return;

            const dx = e.clientX - this._initialX;
            const dy = e.clientY - this._initialY;

            let newLeft = startX;
            let newTop = startY;
            let newWidth = this._initialWidth;
            let newHeight = this._initialHeight;

            switch (direction) {
                case 'n':
                    newTop = startY + dy;
                    newHeight = this._initialHeight - dy;
                    break;
                case 'ne':
                    newTop = startY + dy;
                    newHeight = this._initialHeight - dy;
                    newWidth = this._initialWidth + dx;
                    break;
                case 'e':
                    newWidth = this._initialWidth + dx;
                    break;
                case 'se':
                    newWidth = this._initialWidth + dx;
                    newHeight = this._initialHeight + dy;
                    break;
                case 's':
                    newHeight = this._initialHeight + dy;
                    break;
                case 'sw':
                    newLeft = startX + dx;
                    newWidth = this._initialWidth - dx;
                    newHeight = this._initialHeight + dy;
                    break;
                case 'w':
                    newLeft = startX + dx;
                    newWidth = this._initialWidth - dx;
                    break;
                case 'nw':
                    newLeft = startX + dx;
                    newTop = startY + dy;
                    newWidth = this._initialWidth - dx;
                    newHeight = this._initialHeight - dy;
                    break;
            }

            const minWidth = 125;
            const minHeight = 45;

            if (newWidth < minWidth) {
                newWidth = minWidth;
                if (direction.includes('w')) {
                    newLeft = startX + this._initialWidth - minWidth;
                }
            }

            if (newHeight < minHeight) {
                newHeight = minHeight;
                if (direction.includes('n')) {
                    newTop = startY + this._initialHeight - minHeight;
                }
            }

            this._element.style.left = `${newLeft}px`;
            this._element.style.top = `${newTop}px`;
            this._element.style.width = `${newWidth}px`;
            this._element.style.height = `${newHeight}px`;
        };

        const mouseUpHandler = () => {
            this._isResizing = false;
            this._resizeDirection = null;
            document.removeEventListener('mousemove', mouseMoveHandler);
            document.removeEventListener('mouseup', mouseUpHandler);
        };

        document.addEventListener('mousemove', mouseMoveHandler);
        document.addEventListener('mouseup', mouseUpHandler);
    }

    private _handleDragStart(e: MouseEvent): void {
        if (this._isResizing || e.button !== 0) return;

        const target = e.target as HTMLElement;
        if (!this._titleBarElement.contains(target)) return;

        this._manager.blockWindows();
        this._element.classList.add('dragging');
        this._manager.setActiveWindowDirect(this);

        this._dragging = true;
        this._x = e.clientX;
        this._y = e.clientY;

        document.addEventListener('mousemove', this._mousemoveHandler);
    }

    private _handleDragMove(e: MouseEvent): void {
        if (!this._dragging) return;

        this._dx = e.clientX - this._x;
        this._dy = e.clientY - this._y;

        const rect = this._element.getBoundingClientRect();
        this._element.style.left = `${rect.left + this._dx}px`;
        this._element.style.top = `${rect.top + this._dy}px`;

        this._x = e.clientX;
        this._y = e.clientY;
    }

    private _handleDragEnd(e: MouseEvent): void {
        if (!this._dragging) return;

        this._manager.unblockWindows();
        this._element.classList.remove('dragging');
        this._dragging = false;

        document.removeEventListener('mousemove', this._mousemoveHandler);
    }

    iframeElement(): HTMLIFrameElement {
        return this._frameElement;
    }

    getId(): string {
        return this._id;
    }

    getTitle(): string {
        return this._title;
    }

    getStatusText(): string {
        return this._statusText;
    }

    setTitle(newTitle: string): void {
        this._title = newTitle;
        this._titleElement.innerText = `${newTitle} ${this._statusText}`;
    }

    setStatusText(status: string): void {
        this._statusText = status;
        this._titleElement.innerText = `${this._title} ${status}`;
    }

    block(): void {
        this._maskElement.style.display = 'block';
    }

    unblock(): void {
        this._maskElement.style.display = 'none';
    }

    getElement(): Element {
        return this._element;
    }

    close(): void {
        this._manager.closeWindow(this._id);
        document.removeEventListener('mousemove', this._mousemoveHandler);
    }

    popOut(): void {
        const h = this._frameElement.clientHeight;
        const w = this._frameElement.clientWidth;

        this.close();
        window.open(
            `${import.meta.env.VITE_FRONTEND_URL_PREFIX}/console#${this._id}`, this._title,
            `directories=no,titlebar=no,toolbar=no,location=no,status=no,menubar=no,scrollbars=no,width=${w},height=${h}`
        );
    }

    minimize(): void {
        this._isMinimized = true;
        this._element.style.display = 'none';
        this._titleBarElement.classList.remove('active');
        this._manager.minimizeWindow(this);
    }

    restore(): void {
        this._isMinimized = false;
        this._element.style.display = 'flex';
    }

    reload(): void {
        this.setStatusText('(connecting...)');
        this._frameElement.contentWindow?.location.reload();
    }

    toBack(): void {
        this._titleBarElement.classList.remove('active');
        this._element.style.zIndex = '10000';
        this._isFocused = false;
        this._element.classList.remove('focused');
    }

    toFront(): void {
        this._titleBarElement.classList.add('active');
        this._element.style.zIndex = '20000';
        this._isMinimized = false;
        this._element.style.display = 'flex';
        this._isFocused = true;
        this._element.classList.add('focused');

        this._ensureFocus();
    }

    isInSynth(): boolean {
        return this._inSynth;
    }

    toggleSynth(): void {
        this._inSynth = !this._inSynth;
        if (this._synthControlElement) {
            this._synthControlElement.innerHTML = this._inSynth ? '⌨️✓' : '⌨️';
        }
    }

    write(data: any): void {
        if (this._frameElement?.contentWindow) {
            try {
                this._frameElement.contentWindow.document.dispatchEvent(
                    new CustomEvent<ConsoleEvent>('console', {
                        detail: {
                            type: 'data',
                            id: this._id,
                            data
                        }
                    })
                );
            } catch (e) {
                console.error('Failed to write to iframe:', e);
            }
        }
    }

    private _ensureFocus(): void {
        if (this._frameElement) {
            try {
                this._frameElement.focus();

                if (this._frameElement.contentWindow) {
                    this._frameElement.contentWindow.focus();
                }
            } catch (e) {
                console.log('Cannot focus iframe due to security restrictions');
            }
        }
    }

    focus(): void {
        this._ensureFocus();
    }

    isMinimized(): boolean {
        return this._isMinimized;
    }

    isFocused(): boolean {
        return this._isFocused;
    }
}

/**
 * Console window manager
 */
export class WindowManager {
    private _windows: { [id: string]: Window } = {};
    private _desktop: HTMLDivElement;
    private _taskbar: HTMLDivElement;
    private _zindex: number = 10000;
    private _nextOffset: number = 0;
    private _activeWindowId: string = '';
    private _taskBarChangeEventHandler: (shown: boolean) => void;

    constructor(desktopElement: string, taskbarElement: string) {
        this._desktop = document.getElementById(desktopElement) as HTMLDivElement;
        this._taskbar = document.getElementById(taskbarElement) as HTMLDivElement;

        if (this._desktop) {
            // this._desktop.style.position = 'relative';
            this._desktop.style.width = '100%';
            this._desktop.style.height = '100%';
            this._desktop.style.overflow = 'hidden';
        }
    }

    on(event: WindowManagerEvent, handler: (event: any) => void) {
        if (event == 'taskbarchanges') {
            this._taskBarChangeEventHandler = handler;
        }
    }

    createWindow(id: string, title: string, queryData: IframeQueryData = {cmd: ''}, reload: boolean = false): Window {
        if (this._windows[id]) {
            if (!reload) {
                this.setActiveWindowDirect(this._windows[id]);
                return this._windows[id];
            }
            this._windows[id].close()
        }

        const url = `${import.meta.env.VITE_FRONTEND_URL_PREFIX}/console#${id}?data=${encodeURIComponent(JSON.stringify(queryData))}`

        const win = new Window(
            this,
            id,
            title,
            url,
            10 + this._nextOffset,
            10 + this._nextOffset
        );

        this._desktop.appendChild(win.getElement());
        this._windows[id] = win;

        this.setActiveWindowDirect(win);

        this._nextOffset += 30;
        this._nextOffset %= 300;

        this._updateTaskbar();
        return win;
    }

    closeWindow(id: string): void {
        if (this._windows[id]) {
            this._windows[id].getElement().remove();
            delete this._windows[id];

            if (this._activeWindowId === id) {
                this._activeWindowId = '';
            }

            this._updateTaskbar();
        }
    }

    minimizeWindow(window: Window): void {
        const element = window.getElement() as HTMLElement;
        element.style.display = 'none';

        if (this._activeWindowId === window.getId()) {
            this._activeWindowId = '';
        }

        this._updateTaskbar();
    }

    setActiveWindow(window: Window): void {
        this.setActiveWindowDirect(window);
    }

    setActiveWindowDirect(window: Window): void {
        const windowId = window.getId();

        if (this._activeWindowId === windowId) {
            return;
        }

        const oldActiveId = this._activeWindowId;
        this._activeWindowId = windowId;
        if ((window as any)._isMinimized) {
            window.restore();
        }
        if (oldActiveId && this._windows[oldActiveId]) {
            const oldWindow = this._windows[oldActiveId];
            const oldElement = oldWindow.getElement() as HTMLElement;
            oldElement.style.zIndex = '10000';

            oldWindow.toBack();
        }

        const newElement = window.getElement() as HTMLElement;
        newElement.style.zIndex = '20000';

        window.toFront();
        this._updateTaskbar();
    }

    blockWindows(): void {
        Object.values(this._windows).forEach(win => win.block());
    }

    unblockWindows(): void {
        Object.values(this._windows).forEach(win => win.unblock());
    }

    getWindows(): { [id: string]: Window } {
        return this._windows;
    }

    private _updateTaskbar(): void {
        if (!this._taskbar) return;

        this._taskbar.innerHTML = '';
        const windowIds = Object.keys(this._windows);

        if (windowIds.length === 0) {
            if (this._taskBarChangeEventHandler) {
                this._taskBarChangeEventHandler(false);
            }
            this._taskbar.classList.add('hide');
            return;
        }

        if (this._taskBarChangeEventHandler) {
            this._taskBarChangeEventHandler(true);
        }

        this._taskbar.classList.remove('hide');
        this._taskbar.style.display = 'flex';
        this._taskbar.style.gap = '4px';
        this._taskbar.style.padding = '4px';
        this._taskbar.style.background = '#f5f7fa';
        this._taskbar.style.borderTop = '1px solid #ebeef5';
        this._taskbar.style.overflowX = 'auto';
        this._taskbar.style.overflowY = 'hidden';

        windowIds.forEach(id => {
            const win = this._windows[id];
            const item = document.createElement('button');
            const text = document.createElement('span');

            text.innerText = win.getTitle();
            text.title = win.getTitle();
            text.className = 'taskbar-item-text';
            text.style.fontSize = '12px';
            text.style.whiteSpace = 'nowrap';
            text.style.overflow = 'hidden';
            text.style.textOverflow = 'ellipsis';
            text.style.maxWidth = '120px';

            item.onclick = () => this._handleTaskbarClick(id);
            item.className = 'taskbar-item';
            item.style.padding = '4px 8px';
            item.style.border = '1px solid #dcdfe6';
            item.style.borderRadius = '3px';
            item.style.background = '#ffffff';
            item.style.cursor = 'pointer';
            item.style.transition = 'all 0.2s';
            item.style.minWidth = '60px';
            item.style.flexShrink = '0';

            item.onmouseenter = () => {
                if (id !== this._activeWindowId) {
                    item.style.borderColor = '#409eff';
                }
            };

            item.onmouseleave = () => {
                if (id !== this._activeWindowId) {
                    item.style.borderColor = '#dcdfe6';
                }
            };

            item.appendChild(text);

            if (id === this._activeWindowId) {
                item.classList.add('active');
                item.style.borderColor = '#409eff';
                item.style.background = '#ecf5ff';
            }

            this._taskbar.appendChild(item);
        });
    }

    private _handleTaskbarClick(id: string): void {
        const window = this._windows[id];
        if (!window) return;

        if (this._activeWindowId === id) {
            window.minimize();
        } else {
            this.setActiveWindowDirect(window);
        }
    }
}