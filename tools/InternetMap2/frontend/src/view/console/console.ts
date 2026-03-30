import {Terminal} from 'xterm';
import 'xterm/css/xterm.css';
import '@/style/console/console.css';
import {ConsoleUi} from './ui';
import {ConsoleNetwork} from './network';

export async function initConsole(id: string, term: Terminal) {
    const net = new ConsoleNetwork(id);
    let container
    try {
        container = (await net.getContainer()).result;
    } catch (e) {
        term.write(`error: ${e.result}\r\n`);
        return;
    }

    let meta = container.meta;
    let node = meta.emulatorInfo;

    let info = [];

    info.push({
        label: 'ASN',
        text: node.asn
    });

    info.push({
        label: 'Name',
        text: node.name
    });

    info.push({
        label: 'Role',
        text: node.role
    });

    node.nets.forEach(net => {
        info.push({
            label: 'IP',
            text: `${net.name},${net.address}`
        });
    });

    document.title = `${node.role}: AS${node.asn}/${node.name}`;

    const ui = new ConsoleUi(id, term, `AS${node.asn}/${node.name}`, info);

    if (meta.hasSession) {
        ui.createNotification('Attaching to an existing session; if you don\'t see the shell prompt, try pressing the return key.');
    }

    let ws = net.getSocket();

    ui.attach(ws);
    ui.configureIpc();
}