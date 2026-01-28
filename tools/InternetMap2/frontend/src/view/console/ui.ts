import {Terminal} from 'xterm';
import {AttachAddon} from 'xterm-addon-attach';
import {FitAddon} from 'xterm-addon-fit';
import type {ConsoleEvent} from '@/utils/console-event';
import Hammer from 'hammerjs';

/**
 * console UI controller.
 */
export class ConsoleUi {

    /** pending notifications. */
    private _notifications: string[];

    /** xtermjs object. */
    private _terminal: Terminal;

    /** info panel element. */
    private _infoPanel: HTMLDivElement;

    private _fit: FitAddon;

    /** websocket to console. */
    private _socket: WebSocket;

    /** true if attached to a container. */
    private _attached: boolean;

    /** container id. */
    private _id: string;

    /**
     * construct UI controller.
     *
     * @param id container id.
     * @param term terminal element.
     * @param title title for the infoplate.
     * @param items items for the info plate.
     */
    constructor(id: string, term: Terminal, title: string, items: {
        label: string,
        text: string
    }[]) {
        this._notifications = [];
        this._terminal = term;
        this._id = id;

        let infoPanel = document.createElement('div');
        infoPanel.classList.add('xterm-hover');
        infoPanel.classList.add('tooltip');
        infoPanel.classList.add('right-tooltip');
        infoPanel.classList.add('persistent-tooltip');

        let els = items.map(item => {
            let p = document.createElement('div');

            let l = document.createElement('span');
            l.innerText = item.label;
            l.classList.add('infopanel-label');

            let t = document.createElement('span');
            t.innerText = item.text;
            t.classList.add('infopanel-text');

            p.append(l);
            p.append(t);

            return p;
        });

        let titleElement = document.createElement('div');
        titleElement.classList.add('infopanel-title');
        titleElement.innerText = title;

        let itemsElement = document.createElement('div');
        els.forEach(e => itemsElement.appendChild(e));

        infoPanel.appendChild(titleElement);
        infoPanel.appendChild(itemsElement);

        term.element.appendChild(infoPanel);

        this._infoPanel = infoPanel;

        this._attached = false;

        this._fit = new FitAddon();
        term.loadAddon(this._fit);

        let sizeChange = this._handleSizeChange.bind(this);

        if (window.visualViewport) {
            document.documentElement.addEventListener('touchmove', e => e.preventDefault(), {passive: false});
            window.visualViewport.onresize = function () {
                document.documentElement.style.height = `${this.height}px`;
                sizeChange();
            };
        } else window.onresize = () => sizeChange();
    }

    /**
     * handlw window size change: resize terminal.
     */
    private _handleSizeChange() {
        let dim = this._fit.proposeDimensions()!;
        this._fit.fit();
        if (this._socket && this._socket.readyState == 1) {
            this._socket.send(`\t\r\n\ttermsz;${dim.rows},${dim.cols}`);
        }
    }

    /**
     * draw the next notification.
     */
    private _nextNotification() {
        if (this._notifications.length == 0) return;

        let noteElement = document.createElement('div');
        noteElement.classList.add('xterm-hover');
        noteElement.classList.add('tooltip');
        noteElement.classList.add('bottom-tooltip');

        let textElement = document.createElement('div');
        textElement.innerText = this._notifications.pop() as string;

        noteElement.appendChild(textElement);

        let infoElement = document.createElement('div');
        infoElement.classList.add('muted');
        infoElement.innerText = 'Tap on this message to dismiss.';

        noteElement.appendChild(infoElement);

        let cb = this._nextNotification.bind(this);

        noteElement.onclick = () => {
            noteElement.remove();
            cb();
        };

        this._terminal.element!.appendChild(noteElement);
    }

    /**
     * create new notification. push to queue if one is already showing.
     *
     * @param text notification text.
     */
    createNotification(text: string) {
        this._notifications.push(text);

        if (this._notifications.length == 1) this._nextNotification();
    }

    /**
     * attach to console.
     *
     * @param socket websocket.
     */
    attach(socket: WebSocket) {
        if (this._attached) throw 'already attached.';
        this._attached = true;

        this._socket = socket;

        let attachAddon = new AttachAddon(socket);
        this._terminal.loadAddon(attachAddon);

        window.setTimeout(this._handleSizeChange.bind(this), 1000);

        this._terminal.focus();

        this._socket.addEventListener('error', () => {
            this._terminal.write('\x1b[0;30mConnection reset.\x1b[0m\r\n');
        });

        this._socket.addEventListener('close', () => {
            this._terminal.write('\x1b[0;30mConnection closed by foreign host.\x1b[0m\r\n');
        });

        if ('ontouchstart' in window) {
            this.createNotification('Touchscreen detected - Swipe left/right to move the cursor, double tap to go back in history.')
            let hammer = new Hammer(this._terminal.element as HTMLElement);

            hammer.get('swipe').set({direction: Hammer.DIRECTION_HORIZONTAL});
            hammer.on('swipe', (e) => {
                if (socket.readyState != 1) return;
                switch (e.direction) {
                    case Hammer.DIRECTION_RIGHT:
                        socket.send('\x1b[C');
                        break;
                    case Hammer.DIRECTION_LEFT:
                        socket.send('\x1b[D');
                        break;
                }
            });

            hammer.get('tap').set({taps: 2});
            hammer.on('tap', (e) => {
                if (socket.readyState != 1) return;
                socket.send('\x1b[A');
            });
        }
    }

    /**
     * setup ipc with the windowmanager.
     */
    configureIpc(cmd: string = '') {
        try {
            if (window.self === window.top) return;
        } catch (e) {
            // in frame if error too?
        }

        let parent = window.parent.document;

        let sendReady = () => {
            parent.dispatchEvent(new CustomEvent<ConsoleEvent>('console', {
                detail: {
                    type: 'ready',
                    id: this._id
                }
            }));
            if (cmd && cmd.trim() !== '') {
                setTimeout(() => {
                    this._socket.send(`\n${cmd}\n`)
                }, 1000)
            }
        };

        if (this._socket.readyState === 1) sendReady();
        else this._socket.addEventListener('open', sendReady);

        this._socket.addEventListener('error', () => {
            parent.dispatchEvent(new CustomEvent<ConsoleEvent>('console', {
                detail: {
                    type: 'error',
                    id: this._id
                }
            }));
        });

        this._socket.addEventListener('close', () => {
            parent.dispatchEvent(new CustomEvent<ConsoleEvent>('console', {
                detail: {
                    type: 'closed',
                    id: this._id
                }
            }));
        })

        window.addEventListener('focus', () => {
            parent.dispatchEvent(new CustomEvent<ConsoleEvent>('console', {
                detail: {
                    type: 'focus',
                    id: this._id
                }
            }));
        });

        window.addEventListener('blur', () => {
            parent.dispatchEvent(new CustomEvent<ConsoleEvent>('console', {
                detail: {
                    type: 'blur',
                    id: this._id
                }
            }));
        });

        document.addEventListener('console', (e: CustomEvent<ConsoleEvent>) => {
            let ce: ConsoleEvent = e.detail;
            if (ce.id != this._id) return;
            if (this._socket.readyState != 1) return;
            this._socket.send(ce.data);
        });

        this._terminal.onData((data) => {
            parent.dispatchEvent(new CustomEvent<ConsoleEvent>('console', {
                detail: {
                    type: 'data',
                    id: this._id,
                    data
                }
            }));
        });

        document.addEventListener('keydown', (e) => {
            parent.dispatchEvent(new CustomEvent<ConsoleEvent>('console', {
                detail: {
                    type: 'rawkey',
                    id: this._id,
                    data: e
                }
            }));
        });
    }
};