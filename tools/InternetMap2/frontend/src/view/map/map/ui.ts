import {MapUi as BaseMapUi} from "@/utils/map-ui.ts";
import {DataSource} from "@/view/map/ixMap/datasource.ts";
import type {MapUiConfiguration} from "@/utils/map-ui.ts";

export interface OtherConfiguration {

}

/**
 * map UI controller.
 */
export class MapUi extends BaseMapUi {
    constructor(config: MapUiConfiguration, otherConfig: OtherConfiguration) {
        super(config)
        this.otherConfig = otherConfig;
    }
}