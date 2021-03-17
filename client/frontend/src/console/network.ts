const API_PATH = '/api/v1';

export class ConsoleNetwork {
    private _id: string;

    constructor(id: string) {
        this._id = id;
    }

    async getContainer(): Promise<any> {
        var xhr = new XMLHttpRequest();

        xhr.open('GET', `${API_PATH}/container/${this._id}`);

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
                
                if (res.ok) resolve(res);
                else reject(res);
            };

            xhr.onerror = function () {
                reject({
                    ok: false,
                    result: 'xhr failed.'
                });
            }

            xhr.send();
        });
    }

    getSocket(protocol: string = 'ws'): WebSocket {
        return new WebSocket(`${protocol}://${location.host}${API_PATH}/console/${this._id}`);
    }
};