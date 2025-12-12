import {MapUi as BaseMapUi} from "@/utils/map-ui.ts";
import type {MapUiConfiguration} from "@/utils/map-ui.ts";

export interface OtherConfiguration {

}

/**
 * map UI controller.
 */
export class MapUi extends BaseMapUi {
    public otherConfig: OtherConfiguration
    constructor(config: MapUiConfiguration, otherConfig: OtherConfiguration) {
        super(config)
        this.otherConfig = otherConfig;
    }
}