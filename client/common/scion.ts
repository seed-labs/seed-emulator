import { IPv4, IPv6 } from 'ip-num';
import {Validator} from 'ip-num/Validator';

function tokenize(string: string, pattern: string): string[] {
    const tokenized = string.split(new RegExp(pattern));
    return tokenized.filter(token => token !== ''); // Remove empty strings
}

function paddTo4(x: string | number): string {
    return `${x}`.padStart(4, '0');
}

//   ffaa:1:1067 -> 0xFFAA00011067 -> 281105609592935
function AsFromDottedHex(string: string): number {
    const tokens = tokenize(string, '[:]+');
    const hexStr = '0x' + tokens.map(token => paddTo4(token)).join('');
    return parseInt(hexStr, 16);
}
// output for 281105609592935 -> ffaa:1:1067
function ASToDottedHex(as_num: number): string {
    const result: string[] = [];
    const hexStr = as_num.toString(16);
    let begin = true;
    let encounteredZerosInRow = 0;
    for (let pos = 0; pos < hexStr.length; ) {
      const s = hexStr[pos];
      if (pos !== 0 && pos % 4 === 0 && !begin) {
        result.push(":");
        encounteredZerosInRow = 0;
        begin = true;
      }
      if (begin) {
        if (s === "0") {
          pos++;
          encounteredZerosInRow++;
          if (encounteredZerosInRow === 4) {
            result.push("0", ":");
            begin = true;
            encounteredZerosInRow = 0;
          }
          continue;
        } else {
          result.push(s);
          encounteredZerosInRow = 0;
          begin = false;
          pos++;
        }
      } else {
        result.push(s);
        pos++;
      }
    }
    return result.join("");
  }
/*
// output for 281105609592935 -> ffaa:0001:1067
function ASToDottedHexFull(as_num: number): string {
    const result: string[] = [];
    const hexStr = as_num.toString(16);
    for (let pos = 0; pos < hexStr.length; pos++) {
        const s = hexStr[pos];
        if (pos !== 0 && pos % 4 === 0) {
            result.push(':');
        }
        result.push(s);
    }
    return result.join('');
}*/

/*
representation of SCION internet addresses
i.e.
19-ffaa:1:1067,127.0.0.1:443
17-fe4:1:1067,[2003:f7:a705:50db:de1:a65f:c51:d089]
19-150,[2003:f7:a705:50db:de1:a65f:c51:d089]:8080
*/
export class SCIONAddress {    
    static fromStr(addr: string): SCIONAddress {
        const reg = /^(?:(\d+)-([\d:A-Fa-f]+)),(?:\[([^\]]+)\]|([^\[\]:]+))(?::(\d+))?$/;
        const m = addr.match(reg); // group 1  - isd  , group 2 - asn , group 3 - host_ip , group 4 - port
        let port = 0;
        let asnMatch = m?.[2] ?? '';
        let asn = 0;
        // ASN is dotted hex
        if (asnMatch.includes(':')) {
            asn = AsFromDottedHex(asnMatch);
        } else {
            // ASN is decimal number
            asn = parseInt(asnMatch, 10);
        }

        if ( (m?.length ?? 0 > 4) && (m?.[5] != null) ) {
            port = parseInt(m[5], 10);
        }

        const isd = parseInt(m?.[1] ?? '', 10);        
        const ip = Validator. isValidIPv4String(m?.[4] ?? '')[0] ? new IPv4(m?.[4]) : Validator.isValidIPv6String(m?.[3] ?? '')[0] ? new IPv6(m?.[3]) : undefined;

        return new SCIONAddress(isd, asn, ip, port);
    }

    ia: bigint;
    buf: string;    
    port: number;

    constructor(isd: number, asn: number, ip: IPv4 | IPv6, port = 0) {
        this.ia = BigInt( BigInt(asn) | (BigInt(isd) << BigInt(48)));
        this.buf = ip.toString();        
        this.port = port;
    }

    static fromIAIP(ia: bigint, ip: IPv4 | IPv6, port = 0): SCIONAddress {
        const asn: bigint = ia & BigInt("0x0000FFFFFFFFFFFF");
        const isd: bigint = (ia >> BigInt(48)) & BigInt("0x0000FFFF");

        return new SCIONAddress(Number(isd), Number(asn), ip, port);
    }

    toString(): string {
        const [isd, asn] = this.getIA();
        let asnStr = '';
        if (asn <= 65000) { // asn is BGP AS
            asnStr = asn.toString();
        } else {
            asnStr = ASToDottedHex(asn);
        }
        const ipStr = Validator.isValidIPv6String(this.buf)[0] ? `[${this.buf}]` : this.buf;
        return `${isd}-${asnStr},${ipStr}${this.getPort() !== 0 ? `:${this.getPort()}` : ''}`;
    }

    getIA(): [number, number] {     
        const asn: bigint = this.ia & BigInt("0x0000FFFFFFFFFFFF");
        const isd: bigint = (this.ia >> BigInt(48)) & BigInt("0x0000FFFF");
        
        return [Number(isd), Number(asn)];
    }

    getIP(): IPv4 | IPv6 {     
        return Validator.isValidIPv6String(this.buf)[0] ? new IPv6(this.buf) : new IPv4(this.buf);
    }

    getPort(): number {
        return this.port;
    }
}
