use cardano/transaction.{OutputReference, Transaction}

pub type SensorDatum {
  sensor_id: ByteArray,
}

pub type SensorRedeemer {
  sensor_id: ByteArray,
}

fn sensor_matches(
  datum: Option<SensorDatum>,
  redeemer: SensorRedeemer,
) -> Bool {
  expect Some(sensor_data) = datum

  sensor_data.sensor_id == redeemer.sensor_id
}

validator sensor_validator {
  spend(
    datum: Option<SensorDatum>,
    redeemer: SensorRedeemer,
    _own_ref: OutputReference,
    _self: Transaction,
  ) {
	sensor_matches(datum, redeemer)
  }

  else(_) {
    fail
  }
}

test matching_sensor_id() {
  let datum = Some(SensorDatum { sensor_id: "AGRI_001" })
  let redeemer = SensorRedeemer { sensor_id: "AGRI_001" }

  sensor_matches(datum, redeemer)
}

test different_sensor_id() {
  let datum = Some(SensorDatum { sensor_id: "AGRI_001" })
  let redeemer = SensorRedeemer { sensor_id: "AGRI_002" }

  !sensor_matches(datum, redeemer)
}

test missing_sensor_datum() fail {
  let datum: Option<SensorDatum> = None
  let redeemer = SensorRedeemer { sensor_id: "AGRI_001" }

  sensor_matches(datum, redeemer)
}
