# SPDX-License-Identifier: Apache-2.0

"""Generates `engine_ecu.pdx`/`engine_ecu.odx` — the golden ODX/PDX fixture
for DIAG-06 (issue #55) — via `odxtools`' own object model and
`write_pdx_file()`, rather than hand-written XML.

ODX's schema is deep enough that hand-authoring valid XML directly (the
approach BUS-02 used for its ARXML fixture) would be error-prone; building
the object graph in Python and letting `odxtools` serialize it guarantees
schema validity the same way BUS-01/02 already lean on the wrapped library
as their own oracle. Modeled after `odxtools`' own
`examples/somersaultecu.py` (MIT, github.com/mercedes-benz/odxtools) as an
API-shape reference only — the content here (names, DIDs, structure) is
self-authored for `tapwright`, not copied.

Deterministic and safe to re-run:

    python fixtures/odx/generate_engine_ecu.py

Regenerating and re-verifying the file's `sha256` matches what's recorded
in `fixtures/provenance.toml` is what proves this script wasn't quietly
edited to produce a different fixture than the one review approved.
"""

from __future__ import annotations

import zipfile
from pathlib import Path

import odxtools
from odxtools.audience import Audience
from odxtools.compumethods.compucategory import CompuCategory
from odxtools.compumethods.identicalcompumethod import IdenticalCompuMethod
from odxtools.database import Database
from odxtools.dataobjectproperty import DataObjectProperty
from odxtools.diagdatadictionaryspec import DiagDataDictionarySpec
from odxtools.diaglayercontainer import DiagLayerContainer
from odxtools.diaglayers.diaglayertype import DiagLayerType
from odxtools.diaglayers.ecuvariant import EcuVariant
from odxtools.diaglayers.ecuvariantraw import EcuVariantRaw
from odxtools.diagservice import DiagService
from odxtools.nameditemlist import NamedItemList
from odxtools.odxlink import DocType, OdxDocFragment, OdxLinkId, OdxLinkRef
from odxtools.odxtypes import DataType
from odxtools.parameters.codedconstparameter import CodedConstParameter
from odxtools.parameters.valueparameter import ValueParameter
from odxtools.physicaltype import PhysicalType
from odxtools.request import Request
from odxtools.response import Response, ResponseType
from odxtools.standardlengthtype import StandardLengthType

# The doc fragment's name must match the DiagLayerContainer's own
# short_name below -- a mismatch here fails ODXLINK reference resolution
# on reload with an opaque KeyError, found directly while authoring this
# fixture (see issue #55's closeout for the full story).
DOC_FRAGS = (OdxDocFragment("vehicle_diagnostics", DocType.CONTAINER),)

UINT8 = StandardLengthType(base_data_type=DataType.A_UINT32, bit_length=8)
UINT16 = StandardLengthType(base_data_type=DataType.A_UINT32, bit_length=16)

IDENTICAL_UINT = IdenticalCompuMethod(
    category=CompuCategory.IDENTICAL,
    physical_type=DataType.A_UINT32,
    internal_type=DataType.A_UINT32,
)


def build_database() -> Database:
    engine_speed_dop = DataObjectProperty(
        odx_id=OdxLinkId("EngineECU.DOP.engine_speed", DOC_FRAGS),
        short_name="engine_speed",
        diag_coded_type=UINT16,
        physical_type=PhysicalType(base_data_type=DataType.A_UINT32),
        compu_method=IDENTICAL_UINT,
    )

    read_engine_speed_request = Request(
        odx_id=OdxLinkId("EngineECU.RQ.read_engine_speed", DOC_FRAGS),
        short_name="read_engine_speed",
        long_name="Read the current engine speed (RDBI, DID 0x1234)",
        parameters=[
            CodedConstParameter(
                short_name="sid", diag_coded_type=UINT8, byte_position=0, coded_value_raw=str(0x22)
            ),
            CodedConstParameter(
                short_name="did",
                diag_coded_type=UINT16,
                byte_position=1,
                coded_value_raw=str(0x1234),
            ),
        ],
    )

    engine_speed_response = Response(
        odx_id=OdxLinkId("EngineECU.PR.engine_speed_response", DOC_FRAGS),
        short_name="engine_speed_response",
        response_type=ResponseType.POSITIVE,
        parameters=NamedItemList(
            [
                CodedConstParameter(
                    short_name="sid",
                    diag_coded_type=UINT8,
                    byte_position=0,
                    coded_value_raw=str(0x62),
                ),
                ValueParameter(
                    short_name="engine_speed",
                    byte_position=1,
                    dop_ref=OdxLinkRef.from_id(engine_speed_dop.odx_id),
                ),
            ]
        ),
    )

    read_engine_speed_service = DiagService(
        odx_id=OdxLinkId("EngineECU.service.read_engine_speed", DOC_FRAGS),
        short_name="read_engine_speed",
        semantic="CURRENTDATA",
        request_ref=OdxLinkRef.from_id(read_engine_speed_request.odx_id),
        pos_response_refs=[OdxLinkRef.from_id(engine_speed_response.odx_id)],
    )

    self_test_request = Request(
        odx_id=OdxLinkId("EngineECU.RQ.self_test", DOC_FRAGS),
        short_name="self_test_request",
        long_name="Start the engine self-test routine (RC, routine 0x0203)",
        parameters=[
            CodedConstParameter(
                short_name="sid", diag_coded_type=UINT8, byte_position=0, coded_value_raw=str(0x31)
            ),
            CodedConstParameter(
                short_name="routine_control_type",
                diag_coded_type=UINT8,
                byte_position=1,
                coded_value_raw=str(0x01),
            ),
            CodedConstParameter(
                short_name="routine_id",
                diag_coded_type=UINT16,
                byte_position=2,
                coded_value_raw=str(0x0203),
            ),
        ],
    )

    self_test_service = DiagService(
        odx_id=OdxLinkId("EngineECU.service.self_test", DOC_FRAGS),
        short_name="self_test",
        semantic="ROUTINE",
        request_ref=OdxLinkRef.from_id(self_test_request.odx_id),
        audience=Audience(is_development_raw=False),
    )

    engine_ecu_raw = EcuVariantRaw(
        variant_type=DiagLayerType.ECU_VARIANT,
        odx_id=OdxLinkId("EngineECU.ecu_variant", DOC_FRAGS),
        short_name="EngineECU",
        long_name="Engine control unit (self-authored fixture for DIAG-06)",
        diag_data_dictionary_spec=DiagDataDictionarySpec(
            data_object_props=NamedItemList([engine_speed_dop]),
        ),
        diag_comms_raw=[read_engine_speed_service, self_test_service],
        requests=NamedItemList([read_engine_speed_request, self_test_request]),
        positive_responses=NamedItemList([engine_speed_response]),
    )
    engine_ecu = EcuVariant(diag_layer_raw=engine_ecu_raw)

    dlc = DiagLayerContainer(
        odx_id=OdxLinkId("DLC.vehicle_diagnostics", DOC_FRAGS),
        short_name="vehicle_diagnostics",
        long_name="Self-authored golden ODX fixture for tapwright DIAG-06",
        ecu_variants=NamedItemList([engine_ecu]),
    )

    database = Database()
    database.short_name = "engine_ecu_database"
    database._diag_layer_containers = NamedItemList([dlc])
    database.refresh()
    return database


def main() -> None:
    out_dir = Path(__file__).parent
    pdx_path = out_dir / "engine_ecu.pdx"
    odx_path = out_dir / "engine_ecu.odx"

    odxtools.write_pdx_file(str(pdx_path), build_database())

    # The standalone .odx fixture is the PDX's own inner document, extracted
    # rather than generated by a second path -- one source of truth for both
    # fixture files, so they can never drift apart from each other.
    with zipfile.ZipFile(pdx_path) as archive:
        odx_path.write_bytes(archive.read("vehicle_diagnostics.odx-d"))

    print(f"wrote {pdx_path} and {odx_path}")


if __name__ == "__main__":
    main()
