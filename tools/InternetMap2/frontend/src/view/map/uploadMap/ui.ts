import {DataSource} from './datasource.ts';
import {MapUi as BaseMapUi} from "@/utils/map-ui.ts";
import type {MapUiConfiguration} from "@/utils/map-ui.ts";

export interface UploadMapUiOtherConfiguration {

}

/**
 * map UI controller.
 */
export class MapUi extends BaseMapUi {
    public otherConfig: UploadMapUiOtherConfiguration

    constructor(config: MapUiConfiguration, otherConfig: UploadMapUiOtherConfiguration) {
        super(config)
        this.otherConfig = otherConfig;
        this._datasource = config.datasource as DataSource;
    }

    setVisData(data) {
        this._datasource.setVisData(data)
    }
}