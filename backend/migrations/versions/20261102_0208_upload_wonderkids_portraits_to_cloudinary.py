"""Ingest and host 1,000+ wonderkid portraits on Cloudinary.

Revision ID: 20261102_0208_upload_wonderkids_portraits_to_cloudinary
Revises: 20261102_0207_ingest_and_calibrate_wonderkids_shortlists
Create Date: 2026-11-02 23:30:00
"""

from __future__ import annotations

import json
from alembic import op
import sqlalchemy as sa

revision = "20261102_0208_upload_wonderkids_portraits_to_cloudinary"
down_revision = "20261102_0207_ingest_and_calibrate_wonderkids_shortlists"
branch_labels = None
depends_on = None

# Map of player_id -> (portrait_url, source_provider)
WONDERKID_PORTRAITS: dict[str, tuple[str, str]] = {
    "323765c4-43db-46ad-b289-3a7704147854": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793658378/players/wonderkids/wk_323765c4_pau_cubars.jpg",
        "migrated_to_cloudinary",
    ),
    "c0843527-8b8b-40ee-8792-4c7162e58cc7": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793658378/players/wonderkids/wk_c0843527_pau_cubars__paredes.jpg",
        "migrated_to_cloudinary",
    ),
    "c607e5e3-640a-4156-8fcc-f6a97a69f5ce": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793658377/players/wonderkids/wk_c607e5e3_ayyoub_bouaddi.png",
        "migrated_to_cloudinary",
    ),
    "7349dee2-5456-4093-95a7-0763fd4623dd": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/f_auto,q_auto/gtex/players/37717176",
        "existing_cloudinary",
    ),
    "56276e1a-9970-408a-9d70-eefbe78cc668": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793658377/players/wonderkids/wk_56276e1a_kenan_yildiz.png",
        "migrated_to_cloudinary",
    ),
    "e3fb91ac-e7b3-45f6-99d4-027e910a9035": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/f_auto,q_auto/gtex/players/37598725",
        "existing_cloudinary",
    ),
    "ba45b357-9207-45ef-9cbb-56e228423bbf": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/f_auto,q_auto/gtex/players/37593237",
        "existing_cloudinary",
    ),
    "b2fa5b7d-d213-4848-adc6-1e8d5cf6cc4c": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793658377/players/wonderkids/wk_b2fa5b7d_warren_za_re_emery.png",
        "migrated_to_cloudinary",
    ),
    "e9e150e0-872c-47ad-932e-8cdc500d0dc9": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793656307/players/wonderkids/wk_e9e150e0_aleksandar_pavlovic.png",
        "sofifa_cloudinary",
    ),
    "155accf2-d9c4-42a9-861c-0b67d6c270e1": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/f_auto,q_auto/gtex/players/37582044",
        "sportmonks_cloudinary",
    ),
    "67555782-b7b1-4157-b538-91e3240f21cc": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/f_auto,q_auto/gtex/players/37547467",
        "reused_name_match",
    ),
    "db8c9252-3cbf-4b38-ba90-df032c8a633a": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/f_auto,q_auto/gtex/players/37547467",
        "existing_cloudinary",
    ),
    "2344adb1-c70a-4615-8852-c334e36f2c1c": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/f_auto,q_auto/gtex/players/37612542",
        "existing_cloudinary",
    ),
    "940e6105-e9b2-474f-83da-c3e2b4628768": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793658379/players/wonderkids/wk_940e6105_dean_huijsen.png",
        "migrated_to_cloudinary",
    ),
    "722472bc-4a43-42e8-8c9f-1fd355e29a2f": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793658377/players/wonderkids/wk_722472bc_endrick.png",
        "migrated_to_cloudinary",
    ),
    "5c630eb2-f19d-4bd7-8d9e-7b2c74e297be": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793658376/players/wonderkids/wk_5c630eb2_est_v_o.png",
        "migrated_to_cloudinary",
    ),
    "836a4959-89e8-47f9-af1c-1deae0cffa96": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793658377/players/wonderkids/wk_836a4959_jorrel_hato.png",
        "migrated_to_cloudinary",
    ),
    "8d36642f-7fc4-4605-b3e2-731ca58e3ae3": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793658377/players/wonderkids/wk_8d36642f_kobbie_mainoo.png",
        "migrated_to_cloudinary",
    ),
    "92a56335-ef58-479a-8a48-e1221c9962ab": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/f_auto,q_auto/gtex/players/37600357",
        "existing_cloudinary",
    ),
    "011c72d1-b459-41ac-a47f-1802a6592072": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793658383/players/wonderkids/wk_011c72d1_leny_yoro.png",
        "migrated_to_cloudinary",
    ),
    "ce3957b4-9799-4c0f-8a1f-451a9151bff6": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793656307/players/wonderkids/wk_ce3957b4_samu_omorodion.png",
        "sofifa_cloudinary",
    ),
    "2ac8a578-d1d7-4e00-8ba8-63f1f87cc7b8": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/f_auto,q_auto/gtex/players/37622274",
        "sportmonks_cloudinary",
    ),
    "d5d1073e-e774-4b7f-9c42-e07a83f51272": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/f_auto,q_auto/gtex/players/37531504",
        "existing_cloudinary",
    ),
    "5368d58a-2a68-4770-8d84-fe4995f5503b": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793658382/players/wonderkids/wk_5368d58a_mathys_tel.png",
        "migrated_to_cloudinary",
    ),
    "0c267bc3-950b-498c-909a-b602ac2d5f83": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793656363/players/wonderkids/wk_0c267bc3_rui_araki.jpg",
        "transfermarkt_cloudinary",
    ),
    "58570b60-31db-4b4b-a0e4-34f4fa7c5033": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793656364/players/wonderkids/wk_58570b60_abdellah_ouazane.jpg",
        "transfermarkt_cloudinary",
    ),
    "28ed3989-6f71-4213-8bdc-4248814d6822": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793658382/players/wonderkids/wk_28ed3989_claudio_echeverri.png",
        "migrated_to_cloudinary",
    ),
    "1f955ab2-601a-4890-9d74-dac324ba61a1": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793656144/players/wonderkids/wk_1f955ab2_claudio_jerem_as_echeverri.png",
        "existing_cloudinary",
    ),
    "865a86d4-4818-4073-9d0f-1aca03418f62": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793656364/players/wonderkids/wk_865a86d4_d_ulet_orynbasar.png",
        "transfermarkt_cloudinary",
    ),
    "957487b1-1ada-4d66-933f-1a08c8748965": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/f_auto,q_auto/gtex/players/37568808",
        "existing_cloudinary",
    ),
    "6e40eafa-dcc3-4fad-9df5-687790086110": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793658383/players/wonderkids/wk_6e40eafa_ethan_nwaneri.png",
        "migrated_to_cloudinary",
    ),
    "d7e03137-db8b-4e30-8430-654baf4f3ac1": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793658383/players/wonderkids/wk_d7e03137_franco_mastantuono.png",
        "migrated_to_cloudinary",
    ),
    "4a0bdbd3-89a9-4354-9984-38f5f06a31bb": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/f_auto,q_auto/gtex/players/37729623",
        "existing_cloudinary",
    ),
    "0abd831b-ff11-4134-9564-68e75c787d98": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793658383/players/wonderkids/wk_0abd831b_gabriel_mec.png",
        "migrated_to_cloudinary",
    ),
    "335a34c3-0a04-48b2-8097-091c0a338105": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793656364/players/wonderkids/wk_335a34c3_gabriel_mec.png",
        "transfermarkt_cloudinary",
    ),
    "f1bc13b2-b767-4152-a717-bc70cb5e2f80": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793659133/players/wonderkids/wk_f1bc13b2_lennart_karl.webp",
        "transfermarkt_uploaded",
    ),
    "de427ad7-b891-45dc-9085-94d286660e29": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793658384/players/wonderkids/wk_de427ad7_lucas_bergvall.png",
        "migrated_to_cloudinary",
    ),
    "a1e3d1d2-1e5a-45f1-97d4-6add1dff7d64": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793658389/players/wonderkids/wk_a1e3d1d2_archie_gray.png",
        "migrated_to_cloudinary",
    ),
    "87360e3f-3604-4134-8798-fbced17cae0a": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793658389/players/wonderkids/wk_87360e3f_assan_ou_draogo.png",
        "migrated_to_cloudinary",
    ),
    "d4e75f9a-5f2a-44c5-bfaf-db88ab41ad67": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/f_auto,q_auto/gtex/players/37645043",
        "existing_cloudinary",
    ),
    "c86f078f-0943-42f6-bb2e-e4b40962bdb3": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/f_auto,q_auto/gtex/players/37598726",
        "existing_cloudinary",
    ),
    "a4a3e037-c04b-4a78-bb81-39c508d10b53": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793658387/players/wonderkids/wk_a4a3e037_can_uzun.png",
        "migrated_to_cloudinary",
    ),
    "4f3c78dc-7866-478a-a545-18ff99e58052": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793656369/players/wonderkids/wk_4f3c78dc_cardoso_varela.jpg",
        "transfermarkt_cloudinary",
    ),
    "b8a9a5fd-3953-4ef3-bb98-85b222087202": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793656375/players/wonderkids/wk_b8a9a5fd_dro.jpg",
        "transfermarkt_cloudinary",
    ),
    "849279ef-a4bf-4912-b5fb-73da119d8a7d": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793658383/players/wonderkids/wk_849279ef_francesco_camarda.png",
        "migrated_to_cloudinary",
    ),
    "c0b79f2c-61bc-4629-a8df-924726312044": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/f_auto,q_auto/gtex/players/37656652",
        "sportmonks_cloudinary",
    ),
    "15d6496e-cff8-4e5e-bb99-98efc72ee0aa": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793656369/players/wonderkids/wk_15d6496e_guille_fernandez.jpg",
        "transfermarkt_cloudinary",
    ),
    "cf7d3dcb-b0d7-4f74-9c9e-0ff10914068d": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793656368/players/wonderkids/wk_cf7d3dcb_guille_fern_ndez.jpg",
        "transfermarkt_cloudinary",
    ),
    "ed1ae67c-1aa6-4ee5-afee-6fb8f1ebd187": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793656147/players/wonderkids/wk_ed1ae67c_jayden_danns.png",
        "sofifa_cloudinary",
    ),
    "97477d11-9642-4da1-b325-ba084684a49c": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793658391/players/wonderkids/wk_97477d11_kendry_p_ez.jpg",
        "migrated_to_cloudinary",
    ),
    "b5bbe3de-4744-434b-a0c3-6416c780c0a3": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/f_auto,q_auto/gtex/players/37657587",
        "existing_cloudinary",
    ),
    "fe30a2e0-80c1-4df9-baad-4e2e00633119": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793658384/players/wonderkids/wk_fe30a2e0_luka_vu_kovic.png",
        "migrated_to_cloudinary",
    ),
    "7373fe79-c539-4956-87ad-a8ce8d477aaf": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793658383/players/wonderkids/wk_7373fe79_marc_bernal.png",
        "migrated_to_cloudinary",
    ),
    "f88ed58b-8916-44f6-bc46-278864ba8ace": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/f_auto,q_auto/gtex/players/37710798",
        "existing_cloudinary",
    ),
    "032960bc-eb32-47b8-95bc-d11935d1b4e1": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793656374/players/wonderkids/wk_032960bc_mateus_mide.jpg",
        "transfermarkt_cloudinary",
    ),
    "56bf2b1a-31c4-489e-9454-78ae06718794": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657523/players/wonderkids/wk_56bf2b1a_mattia_liberali.jpg",
        "transfermarkt",
    ),
    "61438463-7285-4f29-a47a-a6a82ea78daf": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793656146/players/wonderkids/wk_61438463_paul_wanner.png",
        "sofifa_cloudinary",
    ),
    "0f1054c1-9bb2-465d-a5f3-9937286f8366": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/f_auto,q_auto/gtex/players/37582045",
        "existing_cloudinary",
    ),
    "a51b1cfe-2abd-49dd-b4c9-a952a7fae5b4": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793656369/players/wonderkids/wk_a51b1cfe_shim_mheuka.jpg",
        "transfermarkt_cloudinary",
    ),
    "d2eb98fd-6940-4e64-bebd-d2d8ebace0cf": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/f_auto,q_auto/gtex/players/37714106",
        "cloudinary",
    ),
    "3e264726-d15b-4955-9c30-2d2d927217ed": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793656363/players/wonderkids/wk_3e264726_toni_fern_ndez.jpg",
        "transfermarkt_cloudinary",
    ),
    "60ce44ac-1037-4a7f-97bb-8eb4e895e52f": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793656369/players/wonderkids/wk_60ce44ac_toni_fern_ndez.jpg",
        "transfermarkt_cloudinary",
    ),
    "15c878b8-d8dc-4b92-af90-759be3f54c30": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793656373/players/wonderkids/wk_15c878b8_amara_diouf.jpg",
        "transfermarkt_cloudinary",
    ),
    "b638bc1d-4354-4cfe-96ed-44304139881f": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793656374/players/wonderkids/wk_b638bc1d_amir_ibragimov.png",
        "transfermarkt_cloudinary",
    ),
    "dd1626a7-3066-494d-9c25-f629a5dd8a79": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793658390/players/wonderkids/wk_dd1626a7_cavan_sullivan.jpg",
        "migrated_to_cloudinary",
    ),
    "aaf33042-efe1-4071-8605-e3cf1c001888": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793658390/players/wonderkids/wk_aaf33042_dastan_satpaev.png",
        "migrated_to_cloudinary",
    ),
    "7a4588b3-c72a-4e26-a8ae-7f401762b166": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793656375/players/wonderkids/wk_7a4588b3_dastan_satpaev.png",
        "existing_cloudinary",
    ),
    "3fbbe07e-6084-43ac-8719-04f1d26cef17": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657523/players/wonderkids/wk_3fbbe07e_konstantinos_karetsas.jpg",
        "transfermarkt",
    ),
    "91a02160-b3ec-4a4a-ac0e-dcb79cae7ce6": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793659134/players/wonderkids/wk_91a02160_lewis_miley.webp",
        "transfermarkt_uploaded",
    ),
    "efbf4bfd-5d4f-4c9c-8d7c-5bdde4ffd947": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793656148/players/wonderkids/wk_efbf4bfd_myles_anthony_lewis_skelly.png",
        "existing_cloudinary",
    ),
    "dbd745fb-fca5-4644-a0ef-fc29d849d602": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793658390/players/wonderkids/wk_dbd745fb_myles_lewis_skelly.png",
        "migrated_to_cloudinary",
    ),
    "db2855f1-03db-4132-acf0-d168e587e549": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/f_auto,q_auto/gtex/players/37577660",
        "sportmonks_cloudinary",
    ),
    "ffdf5db1-ede2-4fa4-8cae-baff8ce9956f": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793656389/players/wonderkids/wk_ffdf5db1_alex_kouto_horio_pisano.jpg",
        "transfermarkt_cloudinary",
    ),
    "ac4aeeb2-a4a0-457e-b27f-74bcb81f5f0e": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793656379/players/wonderkids/wk_ac4aeeb2_alvin_ayman.jpg",
        "transfermarkt_cloudinary",
    ),
    "3add0f10-d51a-4f39-85a2-12c48a72f728": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793656384/players/wonderkids/wk_3add0f10_amir_bouhamdi.jpg",
        "transfermarkt_cloudinary",
    ),
    "d362f3e3-808b-442c-9c0a-c85a4f42cc42": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793658390/players/wonderkids/wk_d362f3e3_chido_obi.png",
        "migrated_to_cloudinary",
    ),
    "bf3fc28e-f0f6-4f04-b084-109efe4e7f14": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793656380/players/wonderkids/wk_bf3fc28e_daniel_banjaqui.jpg",
        "transfermarkt_cloudinary",
    ),
    "02bcebf5-96bd-4997-bf1f-cbe71aa09e74": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793656384/players/wonderkids/wk_02bcebf5_fl_vio_gon_alves.jpg",
        "transfermarkt_cloudinary",
    ),
    "3841f88b-5614-4ad4-91b2-345c4480ca57": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784996003/generated-media/regen_newgen_faces/script_skin_hair/Mixed/Light%20Brown/africa-lightbrown-30.png",
        "gtex_regen_newgen_face_bank",
    ),
    "58e57b0a-2ec3-407d-b111-2ce712cdb78d": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793656380/players/wonderkids/wk_58e57b0a_jan_virgili.jpg",
        "transfermarkt_cloudinary",
    ),
    "3b5653d6-277e-48b7-a15e-7400524a84cd": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793656382/players/wonderkids/wk_3b5653d6_kerem_mat__l.jpg",
        "transfermarkt_cloudinary",
    ),
    "640425f1-f3a8-4785-9dfd-87524b9e31ca": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793658392/players/wonderkids/wk_640425f1_mikey_moore.jpg",
        "migrated_to_cloudinary",
    ),
    "704753d0-2e33-44af-b7ec-8ed66b6f005b": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793656310/players/wonderkids/wk_704753d0_pierce_charles.png",
        "sofifa_cloudinary",
    ),
    "3bf18231-bfaf-4399-a9fe-900f994ccfe9": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793658390/players/wonderkids/wk_3bf18231_rio_ngumoha.png",
        "migrated_to_cloudinary",
    ),
    "040084ba-f131-4c52-bd8d-0842e9f7e865": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/f_auto,q_auto/gtex/players/37656803",
        "sportmonks_cloudinary",
    ),
    "4ca8dbb0-bfdf-478d-8947-02fab798459d": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793656384/players/wonderkids/wk_4ca8dbb0_sebastian_olderheim.jpg",
        "transfermarkt_cloudinary",
    ),
    "c194fd5e-9886-4f4a-8740-2c3a5eadfb22": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793656152/players/wonderkids/wk_c194fd5e_sverre_nypan.png",
        "sofifa_cloudinary",
    ),
    "0922d6ef-73af-442f-a633-b1e6df38d843": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793656379/players/wonderkids/wk_0922d6ef_tom_s_aranda.jpg",
        "transfermarkt_cloudinary",
    ),
    "ee322f3b-7016-4266-a7ed-3c678abb1cea": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793658422/players/wonderkids/wk_ee322f3b_unax_urzaiz.jpg",
        "migrated_to_cloudinary",
    ),
    "0b8b1bda-e20e-45d5-bef6-4caa63887f5b": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793656377/players/wonderkids/wk_0b8b1bda_xavi_espart.jpg",
        "transfermarkt_cloudinary",
    ),
    "fb4f6bfe-670d-460e-9151-d7fc79d4d14a": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793656381/players/wonderkids/wk_fb4f6bfe_yoon_sungjun.jpg",
        "transfermarkt_cloudinary",
    ),
    "93d684b3-84fb-4b38-961d-9178b29af450": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793656384/players/wonderkids/wk_93d684b3_z__lucas.jpg",
        "transfermarkt_cloudinary",
    ),
    "56bd6511-1e1a-46f4-9b13-27f4dfd6bde6": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657523/players/wonderkids/wk_56bd6511_andrea_natali.jpg",
        "existing_cloudinary",
    ),
    "fb7fec02-4fcf-4151-a474-c525ea21f0dd": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657523/players/wonderkids/wk_56bd6511_andrea_natali.jpg",
        "reused_name_match",
    ),
    "9effca47-1761-4080-b333-bd8f93316e00": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793658395/players/wonderkids/wk_9effca47_chris_rigg.png",
        "migrated_to_cloudinary",
    ),
    "16b9c116-511a-4e30-b1b3-ba779b213f0d": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793656389/players/wonderkids/wk_16b9c116_ezra_carrington.jpg",
        "transfermarkt_cloudinary",
    ),
    "7d94d947-4cc1-4252-a89c-fdb57faf874c": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793656389/players/wonderkids/wk_7d94d947_finlay_gorman.jpg",
        "transfermarkt_cloudinary",
    ),
    "bb9ad57c-993f-4de7-a960-4525378d94a9": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793656389/players/wonderkids/wk_bb9ad57c_finlay_gorman.jpg",
        "transfermarkt_cloudinary",
    ),
    "019eac9e-fafa-4217-9527-a3b4b3dff74a": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793656394/players/wonderkids/wk_019eac9e_gonzalo_gross.jpg",
        "transfermarkt_cloudinary",
    ),
    "5031a0c1-d652-49a9-9099-5e5c62536528": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657523/players/wonderkids/wk_5031a0c1_justin_lerma.jpg",
        "transfermarkt",
    ),
    "74b1fd6d-a4ba-4cd9-ad21-ef169a2e378d": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793658392/players/wonderkids/wk_74b1fd6d_max_dowman.jpg",
        "migrated_to_cloudinary",
    ),
    "fdcc0189-0d62-47c1-91bc-ecfe4017bec9": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793658395/players/wonderkids/wk_fdcc0189_max_dowman.jpg",
        "migrated_to_cloudinary",
    ),
    "9718eb73-1f1e-40e3-afb0-ab2ced09b39e": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793656390/players/wonderkids/wk_9718eb73_saba_kharebashvili.png",
        "transfermarkt_cloudinary",
    ),
    "eff52911-6eed-4834-ab1c-a86cb4b6525a": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793658393/players/wonderkids/wk_eff52911_zadok_yohanna.jpg",
        "migrated_to_cloudinary",
    ),
    "d1325930-5ff6-4ca2-b3cd-3e7bdf64bafb": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793656407/players/wonderkids/wk_d1325930_aimar_goved.jpg",
        "transfermarkt_cloudinary",
    ),
    "d890ebff-b7f0-4446-9124-b83e6bb07883": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784995930/generated-media/regen_newgen_faces/script_skin_hair/Mixed/Dark%20Brown/africa-darkbrown-91.png",
        "gtex_regen_newgen_face_bank",
    ),
    "081e3b2e-b152-4e03-8821-3506b5bee684": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793656420/players/wonderkids/wk_081e3b2e_alexis_ciria.jpg",
        "transfermarkt_cloudinary",
    ),
    "ae8ba1ed-4219-440e-8cde-8ee013ba8940": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657525/players/wonderkids/wk_ae8ba1ed_amin_nabizada.jpg",
        "transfermarkt",
    ),
    "56ed5fbc-c3a9-4da9-b9d3-e072c8370e6f": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793656413/players/wonderkids/wk_56ed5fbc_anis_soubeir.jpg",
        "transfermarkt_cloudinary",
    ),
    "81dceae0-7d26-415e-982a-41fb6e1765c7": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793656399/players/wonderkids/wk_81dceae0_antonio_arena.jpg",
        "transfermarkt_cloudinary",
    ),
    "cde467c3-4692-4660-a054-77c9fb93e584": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793656418/players/wonderkids/wk_cde467c3_ayoub_ouarghi.jpg",
        "transfermarkt_cloudinary",
    ),
    "83ba5f23-2e92-4ebf-a779-0fdc0d55f561": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793656426/players/wonderkids/wk_83ba5f23_babis_kostoulas.jpg",
        "transfermarkt_cloudinary",
    ),
    "2adfdec7-39ff-4255-97c6-277838fd4dd3": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793656416/players/wonderkids/wk_2adfdec7_belal_ateya.png",
        "transfermarkt_cloudinary",
    ),
    "c44b75e7-5b20-4ec4-85a2-0ef73e900938": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793656425/players/wonderkids/wk_c44b75e7_bendeg_z_kov_cs.jpg",
        "transfermarkt_cloudinary",
    ),
    "234b8803-1ad5-4240-ac7e-f93fe1d4b4d7": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793656157/players/wonderkids/wk_234b8803_christos_mouzakitis.png",
        "sofifa_cloudinary",
    ),
    "e66e1d34-7472-47e0-b9d4-7d800272d416": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793656405/players/wonderkids/wk_e66e1d34_darlington_osuchukwu.jpg",
        "transfermarkt_cloudinary",
    ),
    "b41fb552-bbf2-448b-bb16-9ccbbe851772": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793656400/players/wonderkids/wk_b41fb552_dastan_satpayev.png",
        "transfermarkt_cloudinary",
    ),
    "8f881402-083c-46eb-9698-d3c25f5a9428": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793656394/players/wonderkids/wk_8f881402_ebrima_tunkara.jpg",
        "transfermarkt_cloudinary",
    ),
    "d5d6feb2-751e-4724-af3d-61e2662ee431": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793656394/players/wonderkids/wk_d5d6feb2_ebrima_tunkara.jpg",
        "transfermarkt_cloudinary",
    ),
    "a9521298-e721-4567-9422-e02829b8eaa5": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793656431/players/wonderkids/wk_a9521298_emanuele_lulli.jpg",
        "transfermarkt_cloudinary",
    ),
    "218c73ff-cf84-465d-ba85-1bf4c5de7b47": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793656399/players/wonderkids/wk_218c73ff_enzo_alves.png",
        "transfermarkt_cloudinary",
    ),
    "49c3b6b9-4d5b-442a-b8e9-8f9ec6c13d56": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784996009/generated-media/regen_newgen_faces/script_skin_hair/Mixed/Light%20Brown/africa-lightbrown-45.png",
        "gtex_regen_newgen_face_bank",
    ),
    "ed6211a0-045c-4c8d-a113-8671895608a8": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793656428/players/wonderkids/wk_ed6211a0_gabriel_wesseh.jpg",
        "transfermarkt_cloudinary",
    ),
    "28273557-e464-46ad-acd5-e39a80b3c8cf": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793656416/players/wonderkids/wk_28273557_gomolemo_kekana.jpg",
        "transfermarkt_cloudinary",
    ),
    "4848c041-b9c3-414e-a306-f3e96b33da07": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793656413/players/wonderkids/wk_4848c041_haruto_nakano.jpg",
        "transfermarkt_cloudinary",
    ),
    "a6a4c861-c4e9-41e1-b8f5-a2f8b4b8c18e": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793656402/players/wonderkids/wk_a6a4c861_hasan_yakub_i_l_in.jpg",
        "transfermarkt_cloudinary",
    ),
    "1750340d-cd1d-4c03-b105-dbaf20613c25": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657512/players/wonderkids/wk_1750340d_jacob_fasida.png",
        "club_direct",
    ),
    "7ecbd4cc-76b3-4390-a0a1-6c219aa11f8f": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/North european/Dark Brown/1099.png",
        "gtex_regen_newgen_face_bank",
    ),
    "a2354f0d-e910-4cfb-a702-32b7a189be6e": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793656423/players/wonderkids/wk_a2354f0d_jamal_iddrissou.jpg",
        "transfermarkt_cloudinary",
    ),
    "51b75c42-6523-4867-a2ec-5bbeb4167f41": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793656486/players/wonderkids/wk_51b75c42_jay_matadeen.jpg",
        "wikimedia_cloudinary",
    ),
    "504e140b-786c-4784-9d67-6619af63bf5f": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793656407/players/wonderkids/wk_504e140b_jerem_as_ochoa.jpg",
        "transfermarkt_cloudinary",
    ),
    "c262de78-9e1e-45ce-b7ef-148b4b7614de": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793656393/players/wonderkids/wk_c262de78_jj_gabriel.jpg",
        "transfermarkt_cloudinary",
    ),
    "fdf23368-5af2-4bf7-9fe1-fe8ce03fc833": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793656393/players/wonderkids/wk_fdf23368_jj_gabriel.jpg",
        "transfermarkt_cloudinary",
    ),
    "3acb4b75-340d-4196-9ec3-9c1ec5bacdd5": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793656417/players/wonderkids/wk_3acb4b75_jorge_cestero.jpg",
        "transfermarkt_cloudinary",
    ),
    "5aa1d2c9-7ba5-4112-862e-3803510974eb": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793656426/players/wonderkids/wk_5aa1d2c9_jos__neto.jpg",
        "transfermarkt_cloudinary",
    ),
    "ff7cfead-1bba-4537-a793-57e72e924d38": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793656421/players/wonderkids/wk_ff7cfead_josh_sonni_lambie.jpg",
        "transfermarkt_cloudinary",
    ),
    "4b1b9491-0a23-4aea-8710-ea50fe646d02": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793656430/players/wonderkids/wk_4b1b9491_kau__moraes.jpg",
        "transfermarkt_cloudinary",
    ),
    "7f53ed4b-7a0c-42fa-a874-72311fe7edf4": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793656154/players/wonderkids/wk_7f53ed4b_keny_arroyo.png",
        "sofifa_cloudinary",
    ),
    "941ec8c4-828f-4863-b0fb-c916132e182d": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793656429/players/wonderkids/wk_941ec8c4_kieran_morrison.jpg",
        "transfermarkt_cloudinary",
    ),
    "19c3d59c-e51c-42e7-938e-ec2fbc39c7c6": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793656403/players/wonderkids/wk_19c3d59c_lacin__megnan.png",
        "transfermarkt_cloudinary",
    ),
    "a4da5fec-2745-4617-bbb2-5f28e974b10f": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793656433/players/wonderkids/wk_a4da5fec_lazola_maku.jpg",
        "transfermarkt_cloudinary",
    ),
    "8f1ade2e-619c-4d1b-a95d-020ff10e2aae": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793656412/players/wonderkids/wk_8f1ade2e_leonardo_bovio.jpg",
        "transfermarkt_cloudinary",
    ),
    "37860f6a-a62a-43bd-911b-a568a345dd0b": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793656412/players/wonderkids/wk_37860f6a_luca_vozar.jpg",
        "transfermarkt_cloudinary",
    ),
    "b9ee6d59-e1ec-4bc0-9456-898083e8f1f1": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793656403/players/wonderkids/wk_b9ee6d59_luis_fragozo.jpg",
        "transfermarkt_cloudinary",
    ),
    "e165ebf9-febb-460d-a30c-865b5212a03f": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793656413/players/wonderkids/wk_e165ebf9_mario_rivas.jpg",
        "transfermarkt_cloudinary",
    ),
    "d95a0fd1-1114-47e0-9411-30acf09d4b96": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793656432/players/wonderkids/wk_d95a0fd1_mathis_mout.jpg",
        "transfermarkt_cloudinary",
    ),
    "398f3d22-2919-43b3-b6f7-b46a8b9b96a0": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784995975/generated-media/regen_newgen_faces/script_skin_hair/Mixed/Light%20Brown/africa-lightbrown-185.png",
        "gtex_regen_newgen_face_bank",
    ),
    "139f17cc-866f-49f4-a761-ab40f0f3492e": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793656407/players/wonderkids/wk_139f17cc_michal_zuk.jpg",
        "transfermarkt_cloudinary",
    ),
    "b7a0e765-2fd9-42b6-b035-ebdb2f16e954": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793656314/players/wonderkids/wk_b7a0e765_mohamed_me_t.png",
        "sofifa_cloudinary",
    ),
    "309fb272-b3af-4c96-af09-449bfca45fbb": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793656399/players/wonderkids/wk_309fb272_mono_mart_nez.jpg",
        "transfermarkt_cloudinary",
    ),
    "29bd4e63-95ef-423a-8523-79c2464cf3cb": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793656420/players/wonderkids/wk_29bd4e63_mpho_padime.jpg",
        "transfermarkt_cloudinary",
    ),
    "cc08c6c2-0b0c-4726-9a90-a79b53ca89af": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793656401/players/wonderkids/wk_cc08c6c2_pedro_rodr_guez.jpg",
        "transfermarkt_cloudinary",
    ),
    "66d60c6e-8e7a-43a2-af57-04d76dd561d2": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784995977/generated-media/regen_newgen_faces/script_skin_hair/Mixed/Light%20Brown/africa-lightbrown-194.png",
        "gtex_regen_newgen_face_bank",
    ),
    "2638d102-04ad-4c52-a6ad-198b2cb51e1b": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793656416/players/wonderkids/wk_2638d102_rafael_quintas.jpg",
        "transfermarkt_cloudinary",
    ),
    "dbe394fa-0175-4d2e-92a6-c77419bbed40": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/South european/Dark Brown/248.png",
        "gtex_regen_newgen_face_bank",
    ),
    "8a4d0941-5929-49db-883b-7412d60fd08b": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/f_auto,q_auto/gtex/players/37722794",
        "existing_cloudinary",
    ),
    "909be77b-dda0-413c-9503-98dde6b3d096": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657523/players/wonderkids/wk_909be77b_sean_steur.jpg",
        "transfermarkt",
    ),
    "31610e47-a352-4208-abdb-35f5f369270b": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657523/players/wonderkids/wk_31610e47_sean_steur.jpg",
        "transfermarkt",
    ),
    "85fb4905-41ba-46a3-b1a6-9cf3696a7b38": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793656428/players/wonderkids/wk_85fb4905_thato_sibiya.jpg",
        "transfermarkt_cloudinary",
    ),
    "7828e81f-32c2-4941-904b-74e6fd5d604e": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793656408/players/wonderkids/wk_7828e81f_trevor_benedict.jpg",
        "transfermarkt_cloudinary",
    ),
    "3bdd3d47-b6fe-4ed0-a5b6-dd3bac999e91": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793656430/players/wonderkids/wk_3bdd3d47_vakhtang_salia.png",
        "transfermarkt_cloudinary",
    ),
    "340cfb5a-2305-414d-82fa-665553ea8f3e": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793656425/players/wonderkids/wk_340cfb5a_viktor_bjarki_da_ason.jpg",
        "transfermarkt_cloudinary",
    ),
    "b9800c97-51aa-4585-8476-e70214c591fd": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793656403/players/wonderkids/wk_b9800c97_xavier_parker.jpg",
        "transfermarkt_cloudinary",
    ),
    "864c817a-ed18-4c79-bc08-34fbf90e4d4c": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784995761/generated-media/regen_newgen_faces/script_skin_hair/Mixed/Black/africa-black-215.png",
        "gtex_regen_newgen_face_bank",
    ),
    "84c3ad38-8f13-4a3c-972b-c171c9b04ef3": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793656156/players/wonderkids/wk_84c3ad38_yunus_emre_konak.png",
        "sofifa_cloudinary",
    ),
    "30df4e3a-7c67-4896-b0ba-817f3b7d0fef": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793656434/players/wonderkids/wk_30df4e3a_alec_shabany.jpg",
        "transfermarkt_cloudinary",
    ),
    "d51dcae5-9ca5-4c51-b531-dfe3e74e8308": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793656315/players/wonderkids/wk_d51dcae5_dylan_smith.png",
        "sofifa_cloudinary",
    ),
    "2b856398-9cc3-483d-9fca-34f8f1789ebc": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/f_auto,q_auto/gtex/players/37656061",
        "existing_cloudinary",
    ),
    "90a42933-9174-4af1-995c-43dc073cdc5a": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793658395/players/wonderkids/wk_90a42933_ethan_mbapp.png",
        "migrated_to_cloudinary",
    ),
    "547aea2b-2f3d-4fe2-88b7-8d35ff885786": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657515/players/wonderkids/wk_547aea2b_isaac_holland.png",
        "club_direct",
    ),
    "7cd79b99-09dd-49cf-b3b2-8a0ccd2656a4": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/North european/Dark Brown/544.png",
        "gtex_regen_newgen_face_bank",
    ),
    "1c320d64-5091-44c5-ab9b-30d06b939f31": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793656439/players/wonderkids/wk_1c320d64_quincy_hoquee.png",
        "transfermarkt_cloudinary",
    ),
    "239561e7-1ae9-418a-98a4-c2025b5e0691": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793656433/players/wonderkids/wk_239561e7_shane_kluivert.jpg",
        "transfermarkt_cloudinary",
    ),
    "86b86365-3b84-4aac-b682-e58ecc1a2dcf": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784995760/generated-media/regen_newgen_faces/script_skin_hair/Mixed/Black/africa-black-210.png",
        "gtex_regen_newgen_face_bank",
    ),
    "f5593ba3-f6e3-42bf-999f-d5f78a23c052": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/f_auto,q_auto/gtex/players/37707110",
        "sportmonks_cloudinary",
    ),
    "f5e47aa0-54ac-49c6-ad29-f1f571b1b3f8": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784995859/generated-media/regen_newgen_faces/script_skin_hair/Mixed/Dark%20Brown/africa-darkbrown-16.png",
        "gtex_regen_newgen_face_bank",
    ),
    "c2a7ab1e-282d-4b4f-9bfe-1fcae85b479b": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793656533/players/wonderkids/wk_c2a7ab1e_alan_mwamba.jpg",
        "wikimedia_cloudinary",
    ),
    "c357e141-c104-4e2b-865b-be15f08017d1": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793656315/players/wonderkids/wk_c357e141_alejandro_santiago.png",
        "sofifa_cloudinary",
    ),
    "8bbe67e7-04b3-4381-82d0-fe41bcafa1ea": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793656474/players/wonderkids/wk_8bbe67e7_alessio_baralla.jpg",
        "transfermarkt_cloudinary",
    ),
    "20ae66be-3f48-43d4-9607-f09ed1aa11c2": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793656537/players/wonderkids/wk_20ae66be_lvaro_lezcano.jpg",
        "wikimedia_cloudinary",
    ),
    "5d4a6780-cdea-4a6b-92b7-dc6a351ea018": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657538/players/wonderkids/wk_5d4a6780_amadou_niang.jpg",
        "transfermarkt",
    ),
    "89c39102-8bb7-41ba-b1c7-b344f6a30015": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793656517/players/wonderkids/wk_89c39102_anai.jpg",
        "wikimedia_cloudinary",
    ),
    "94bbf599-573a-4963-b59f-6898b5c99ded": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657557/players/wonderkids/wk_94bbf599_andr__miranda.jpg",
        "transfermarkt",
    ),
    "0e89f80e-c492-4a43-8e8e-7166db912079": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793656173/players/wonderkids/wk_0e89f80e_anto_ito_cordero.png",
        "sofifa_cloudinary",
    ),
    "b7a4c5f1-b5bb-454c-b179-1c50b0f5e7bf": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793656475/players/wonderkids/wk_b7a4c5f1_arman_durmi_i.jpg",
        "transfermarkt_cloudinary",
    ),
    "49e0e2d1-e6ea-492c-9d08-62b198226242": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793656163/players/wonderkids/wk_49e0e2d1_arnu.png",
        "sofifa_cloudinary",
    ),
    "917584d9-106e-4cc3-b909-b3b94add9f18": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657532/players/wonderkids/wk_917584d9_arthur_dias.jpg",
        "transfermarkt",
    ),
    "e6fc5193-a7d9-4c14-b26b-36dc424d4856": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784995931/generated-media/regen_newgen_faces/script_skin_hair/Mixed/Dark%20Brown/africa-darkbrown-97.png",
        "gtex_regen_newgen_face_bank",
    ),
    "cf10a7ef-8051-4d4c-b252-bef516d06902": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657533/players/wonderkids/wk_cf10a7ef_bade_aluko.jpg",
        "transfermarkt",
    ),
    "d46c6b2c-7837-4125-a6cd-e996042f573d": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657546/players/wonderkids/wk_d46c6b2c_brian_fari_as.jpg",
        "transfermarkt",
    ),
    "c0f8ee66-9057-4a43-b61d-18937f394c2e": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793656463/players/wonderkids/wk_c0f8ee66_brian_madjo.jpg",
        "transfermarkt_cloudinary",
    ),
    "6ca411e4-514c-4f16-83c8-886d53f19f31": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784995956/generated-media/regen_newgen_faces/script_skin_hair/Mixed/Light%20Brown/africa-lightbrown-141.png",
        "gtex_regen_newgen_face_bank",
    ),
    "db86f0c6-ec82-4dbb-9736-499057e827e4": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793656468/players/wonderkids/wk_db86f0c6_bryan_bugar_n.jpg",
        "transfermarkt_cloudinary",
    ),
    "00bba2a3-1731-4b5f-b1f5-db7fca363899": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793656473/players/wonderkids/wk_00bba2a3_callum_olusesi.jpg",
        "transfermarkt_cloudinary",
    ),
    "27051ef4-37a8-45bf-bfa6-e89db57996f0": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793656449/players/wonderkids/wk_27051ef4_christian_lupo.jpg",
        "transfermarkt_cloudinary",
    ),
    "233d9a51-6eb2-404d-ac79-2acf9f24c180": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793656319/players/wonderkids/wk_233d9a51_christopher_olivier.png",
        "sofifa_cloudinary",
    ),
    "1a32b359-b8db-4a77-abea-99af18301231": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784995774/generated-media/regen_newgen_faces/script_skin_hair/Mixed/Black/africa-black-246.png",
        "gtex_regen_newgen_face_bank",
    ),
    "388e6c55-4b54-4871-b8cc-edbff95ccc75": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793656447/players/wonderkids/wk_388e6c55_connor_dale.jpg",
        "transfermarkt_cloudinary",
    ),
    "52cc8628-cd51-4a2e-ac8b-112dfb41eca5": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657538/players/wonderkids/wk_52cc8628_daniel_budesca.jpg",
        "transfermarkt",
    ),
    "80a2fa63-1ff0-44c7-9e60-3b928261a0b2": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784995918/generated-media/regen_newgen_faces/script_skin_hair/Mixed/Dark%20Brown/africa-darkbrown-70.png",
        "gtex_regen_newgen_face_bank",
    ),
    "bc59a683-2a31-4599-b5be-4cf10de7ddae": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793656441/players/wonderkids/wk_bc59a683_david_eze.png",
        "transfermarkt_cloudinary",
    ),
    "16413275-693f-4515-856d-78861ef6cede": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793656466/players/wonderkids/wk_16413275_deinner_ord__ez.jpg",
        "transfermarkt_cloudinary",
    ),
    "a546e63a-1b41-4327-a26e-013b1acd4ccd": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784995922/generated-media/regen_newgen_faces/script_skin_hair/Mixed/Dark%20Brown/africa-darkbrown-77.png",
        "gtex_regen_newgen_face_bank",
    ),
    "e39f9dbf-ea29-4b86-8476-e1c3d0750175": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784995729/generated-media/regen_newgen_faces/script_skin_hair/Mixed/Black/africa-black-136.png",
        "gtex_regen_newgen_face_bank",
    ),
    "08a8fb08-b00f-4989-a6b7-a8f790f6977c": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784995994/generated-media/regen_newgen_faces/script_skin_hair/Mixed/Light%20Brown/africa-lightbrown-231.png",
        "gtex_regen_newgen_face_bank",
    ),
    "7bd23db9-b455-4988-8bb8-91eaeaf0a2e3": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793656528/players/wonderkids/wk_7bd23db9_diego_mascardi.jpg",
        "wikimedia_cloudinary",
    ),
    "b03c7b43-db5e-4f85-adae-39c673091447": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784995982/generated-media/regen_newgen_faces/script_skin_hair/Mixed/Light%20Brown/africa-lightbrown-204.png",
        "gtex_regen_newgen_face_bank",
    ),
    "c701a75c-567c-404c-a4b0-219af36410b7": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793656521/players/wonderkids/wk_c701a75c_eddy_dou.png",
        "wikimedia_cloudinary",
    ),
    "7f2aed73-28df-4fd6-a81e-50de6fef4727": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784995948/generated-media/regen_newgen_faces/script_skin_hair/Mixed/Light%20Brown/africa-lightbrown-130.png",
        "gtex_regen_newgen_face_bank",
    ),
    "c4c1a192-b144-4b05-b09a-fba559f34a49": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793656453/players/wonderkids/wk_c4c1a192_eduardo_concei__o.jpg",
        "transfermarkt_cloudinary",
    ),
    "61f70f09-a740-49b7-b846-d60dde1389da": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793656442/players/wonderkids/wk_61f70f09_eduardo_pape.jpg",
        "transfermarkt_cloudinary",
    ),
    "e7939a92-a040-4e1d-90ce-9bb8dd1dddc1": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793656465/players/wonderkids/wk_e7939a92_edwin_quintero.jpg",
        "transfermarkt_cloudinary",
    ),
    "a9cbb5b5-d351-4bcf-803a-0e06dedbe860": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793656470/players/wonderkids/wk_a9cbb5b5_eirik_granaas.jpg",
        "transfermarkt_cloudinary",
    ),
    "461dc3bc-3ffa-42a0-84b3-697844e1ad2f": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793656439/players/wonderkids/wk_461dc3bc_elias_arden.jpg",
        "transfermarkt_cloudinary",
    ),
    "3ca2b965-34d1-49db-9d8a-d70351f32c3f": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657533/players/wonderkids/wk_3ca2b965_enoch_mastoras.jpg",
        "transfermarkt",
    ),
    "40cd19d2-42ca-4a3a-9a56-463758d4b675": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793656460/players/wonderkids/wk_40cd19d2_fabricio_prado.jpg",
        "transfermarkt_cloudinary",
    ),
    "ec519d15-043a-4ba6-847c-81711cb38da8": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793656318/players/wonderkids/wk_ec519d15_faton_ademi.png",
        "sofifa_cloudinary",
    ),
    "e0526701-28a0-45bd-b93f-ab8579f619d3": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793656454/players/wonderkids/wk_e0526701_federico_croci.jpg",
        "transfermarkt_cloudinary",
    ),
    "22cd286d-2491-4327-add4-ef00b32dd1fb": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793656446/players/wonderkids/wk_22cd286d_federico_steffanoni.jpg",
        "transfermarkt_cloudinary",
    ),
    "37d079b3-f81b-4f5e-8416-6fafeea116ff": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784995982/generated-media/regen_newgen_faces/script_skin_hair/Mixed/Light%20Brown/africa-lightbrown-201.png",
        "gtex_regen_newgen_face_bank",
    ),
    "bb20fb69-a686-47fe-8c90-013b5a174dab": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657555/players/wonderkids/wk_bb20fb69_gabri_valero.jpg",
        "transfermarkt",
    ),
    "09ef7067-cd18-49ca-9226-155daadcc31b": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784996018/generated-media/regen_newgen_faces/script_skin_hair/Mixed/Light%20Brown/africa-lightbrown-70.png",
        "gtex_regen_newgen_face_bank",
    ),
    "c4d3a5c1-2d63-4871-bf4a-4db5e7bf6804": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657547/players/wonderkids/wk_c4d3a5c1_george_abbott.jpg",
        "transfermarkt",
    ),
    "cd7ec16c-7cc1-48d9-b69f-bd48861a0a16": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784996018/generated-media/regen_newgen_faces/script_skin_hair/Mixed/Light%20Brown/africa-lightbrown-71.png",
        "gtex_regen_newgen_face_bank",
    ),
    "1f436cae-d4fc-4072-a417-ed4e5f578b5b": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793656316/players/wonderkids/wk_1f436cae_hessel_de_wit.png",
        "sofifa_cloudinary",
    ),
    "b6f4b4df-b07b-4b38-a487-c2512a22e551": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784995761/generated-media/regen_newgen_faces/script_skin_hair/Mixed/Black/africa-black-213.png",
        "gtex_regen_newgen_face_bank",
    ),
    "0cb9f6e1-7e4f-4c63-8e18-386dd41cff7c": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657536/players/wonderkids/wk_0cb9f6e1_igor_felisberto.jpg",
        "transfermarkt",
    ),
    "e72ffc5e-7c93-4be0-af8f-8366f442cba4": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793656449/players/wonderkids/wk_e72ffc5e_ihor_galdin.jpg",
        "transfermarkt_cloudinary",
    ),
    "2dad1320-d4b7-4d21-a4c4-ec6c294c9005": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784995761/generated-media/regen_newgen_faces/script_skin_hair/Mixed/Black/africa-black-211.png",
        "gtex_regen_newgen_face_bank",
    ),
    "bb31e780-f33c-4254-8cb2-3694e46efae0": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793656461/players/wonderkids/wk_bb31e780_jakov_dedi.jpg",
        "transfermarkt_cloudinary",
    ),
    "9f1cf8b9-e343-4325-a3a0-1c337c11bf72": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784995997/generated-media/regen_newgen_faces/script_skin_hair/Mixed/Light%20Brown/africa-lightbrown-239.png",
        "gtex_regen_newgen_face_bank",
    ),
    "f0bdaa3e-ec0e-45c4-a706-764054b6e58d": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657553/players/wonderkids/wk_f0bdaa3e_jesse_bisiwu.jpg",
        "transfermarkt",
    ),
    "9b9774ac-8052-4073-9406-a799287fcc06": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657558/players/wonderkids/wk_9b9774ac_jim_thwaites.jpg",
        "transfermarkt",
    ),
    "ce2f057b-c50f-4385-9c3b-91fc159ee248": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793656454/players/wonderkids/wk_ce2f057b_jivayno_zinhagel.jpg",
        "transfermarkt_cloudinary",
    ),
    "4ac7562e-1def-4fe7-bb11-487514480a0c": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657560/players/wonderkids/wk_4ac7562e_jo_o_borne.png",
        "transfermarkt",
    ),
    "6fc9f462-b95f-4325-8099-29385b5851c3": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657546/players/wonderkids/wk_6fc9f462_jo_o_cruz.jpg",
        "transfermarkt",
    ),
    "c784d6d0-771a-481c-ab4c-3936f8e499d1": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657545/players/wonderkids/wk_c784d6d0_jo_o_sim_es.jpg",
        "transfermarkt",
    ),
    "8a845f14-ecae-4ac9-9d3b-bf7f06572871": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657554/players/wonderkids/wk_8a845f14_johannes_moser.png",
        "transfermarkt",
    ),
    "2a6bee19-fb07-44d8-be33-3419b9b59f2f": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793656454/players/wonderkids/wk_2a6bee19_jos__escorcia.jpg",
        "transfermarkt_cloudinary",
    ),
    "09d9f703-627a-45a7-9667-74e964f03ec9": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657533/players/wonderkids/wk_09d9f703_josh_stephenson.jpg",
        "transfermarkt",
    ),
    "44bb5463-1adb-477d-bea3-ff97a603bef8": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793656443/players/wonderkids/wk_44bb5463_joshua_nga_kana.jpg",
        "transfermarkt_cloudinary",
    ),
    "abca9f50-f3ca-4194-ac9f-732af3c7d461": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657565/players/wonderkids/wk_abca9f50_juan_riquelme_angulo.jpg",
        "transfermarkt",
    ),
    "54d88a32-9dec-436d-9109-e75bf099b6c2": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793656525/players/wonderkids/wk_54d88a32_jules_ahoka.jpg",
        "wikimedia_cloudinary",
    ),
    "5b268533-80a6-4f35-8b1a-05b420bb9fef": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657558/players/wonderkids/wk_5b268533_julian_oerip.jpg",
        "transfermarkt",
    ),
    "ff44a450-7b12-496c-9553-a4546da05841": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793656439/players/wonderkids/wk_ff44a450_junior_mandza.jpg",
        "transfermarkt_cloudinary",
    ),
    "7ca041fa-1334-4b7c-89a7-875105b38f7f": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657568/players/wonderkids/wk_7ca041fa_kau__elias.png",
        "transfermarkt",
    ),
    "090105c1-7c2e-4d32-8b18-019bea750296": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657537/players/wonderkids/wk_090105c1_leo_shahar.jpg",
        "transfermarkt",
    ),
    "a79cc1bc-0df3-4345-9aa1-8985e29b3e27": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657532/players/wonderkids/wk_a79cc1bc_leon_jakirovi.jpg",
        "transfermarkt",
    ),
    "64c3422d-e0a7-4698-a247-9ffb26eeac5e": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657556/players/wonderkids/wk_64c3422d_leonel_flores.jpg",
        "transfermarkt",
    ),
    "d482f56c-db44-4aef-9545-268e4045c392": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784995780/generated-media/regen_newgen_faces/script_skin_hair/Mixed/Black/africa-black-4.png",
        "gtex_regen_newgen_face_bank",
    ),
    "f166e935-8c15-40f6-97ea-19c4ebc4b877": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657537/players/wonderkids/wk_f166e935_luca_erlein.jpg",
        "transfermarkt",
    ),
    "4f6636bf-228d-44b1-b1d5-91d14703d84f": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793656478/players/wonderkids/wk_4f6636bf_luca_meirelles.png",
        "transfermarkt_cloudinary",
    ),
    "83c1bf2c-c07d-402e-8731-0844e21f7067": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657540/players/wonderkids/wk_83c1bf2c_lucas_rodrigues.jpg",
        "transfermarkt",
    ),
    "849de299-7335-4a67-8ed3-8b691c78f24b": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657552/players/wonderkids/wk_849de299_lucas_rosier.jpg",
        "transfermarkt",
    ),
    "7c6d085f-bd1d-4ad7-a937-e036c5886c39": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657531/players/wonderkids/wk_7c6d085f_lucca_brughmans.jpg",
        "transfermarkt",
    ),
    "dcbf32fd-efa2-444f-ab40-af8749db5b9f": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657557/players/wonderkids/wk_dcbf32fd_luke_baartman.jpg",
        "transfermarkt",
    ),
    "50f77e44-fce4-4c64-91c8-2219d9364147": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657535/players/wonderkids/wk_50f77e44_lushendry_martes.jpg",
        "transfermarkt",
    ),
    "a1d5aa4b-493b-458f-b564-f9c2b85a3606": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784995911/generated-media/regen_newgen_faces/script_skin_hair/Mixed/Dark%20Brown/africa-darkbrown-4.png",
        "gtex_regen_newgen_face_bank",
    ),
    "f8cccdf6-3dde-48e2-8fdf-882315a3382e": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793656459/players/wonderkids/wk_f8cccdf6_mateo_garrido.jpg",
        "transfermarkt_cloudinary",
    ),
    "dc616497-6b15-4f00-ba9f-7da331ff5d34": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793656540/players/wonderkids/wk_dc616497_matheus_gon_alves.png",
        "wikimedia_cloudinary",
    ),
    "4be7fdb6-9984-48b1-89d2-41c09214fe46": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657540/players/wonderkids/wk_4be7fdb6_mat_as_orozco.jpg",
        "transfermarkt",
    ),
    "c8a82bdd-3c44-4888-bc5a-7dfbf7e1fe2f": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793656453/players/wonderkids/wk_c8a82bdd_matou__srb.jpg",
        "transfermarkt_cloudinary",
    ),
    "e2815448-24bb-4714-976d-302cea850cec": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793656475/players/wonderkids/wk_e2815448_mattia_mosconi.jpg",
        "transfermarkt_cloudinary",
    ),
    "e5c1fbb0-eecf-4969-a6d6-dbfe1d37bf44": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657542/players/wonderkids/wk_e5c1fbb0_mauricio_amaro.jpg",
        "transfermarkt",
    ),
    "808e3a77-0450-4efd-83ab-47a897b76e74": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793656467/players/wonderkids/wk_808e3a77_mezian_mesloub.jpg",
        "transfermarkt_cloudinary",
    ),
    "ee6d9aa0-12aa-4379-88df-e4551e0b47fd": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793656479/players/wonderkids/wk_ee6d9aa0_miguel_marulanda.jpg",
        "transfermarkt_cloudinary",
    ),
    "dd6da90d-ae45-4250-90e8-400ef72c0404": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784995805/generated-media/regen_newgen_faces/script_skin_hair/Mixed/Black/africa-black-95.png",
        "gtex_regen_newgen_face_bank",
    ),
    "5ee8d652-81ea-42dc-8344-5981d9151b12": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657559/players/wonderkids/wk_5ee8d652_mladen_mijajlovi.jpg",
        "transfermarkt",
    ),
    "3ae93078-b407-42d0-a49d-c735ab50ebcd": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793656176/players/wonderkids/wk_3ae93078_mohamed_abdalla.png",
        "sofifa_cloudinary",
    ),
    "0dfa62f1-fa4e-498c-9bd2-392b226201fe": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784995766/generated-media/regen_newgen_faces/script_skin_hair/Mixed/Black/africa-black-223.png",
        "gtex_regen_newgen_face_bank",
    ),
    "c3410598-5ba7-47df-a6f0-a5d2ef61fd05": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793656448/players/wonderkids/wk_c3410598_mohanad_el_shamy.png",
        "transfermarkt_cloudinary",
    ),
    "5568edc4-6275-4104-92b4-f5163d1cc3ad": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657531/players/wonderkids/wk_5568edc4_mor_talla_ndiaye.jpg",
        "transfermarkt",
    ),
    "f941b91b-0ecf-4a6f-b580-452c85b7b2d3": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784995813/generated-media/regen_newgen_faces/script_skin_hair/Mixed/Blonde/africa-blonde-30.png",
        "gtex_regen_newgen_face_bank",
    ),
    "8ad9be8b-1ab5-45c6-aa9e-012829b7d983": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793656443/players/wonderkids/wk_8ad9be8b_nacho_p_rez.jpg",
        "transfermarkt_cloudinary",
    ),
    "c6a441c6-c94d-4c0e-a803-5e9c0f8b05f0": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784995908/generated-media/regen_newgen_faces/script_skin_hair/Mixed/Dark%20Brown/africa-darkbrown-50.png",
        "gtex_regen_newgen_face_bank",
    ),
    "eed75d8e-fccf-4d5b-84dc-152365fa84d7": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657530/players/wonderkids/wk_eed75d8e_nico_biedermann.jpg",
        "transfermarkt",
    ),
    "e67ebea0-a81d-4e0d-bee1-4a8e1aa93458": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657545/players/wonderkids/wk_e67ebea0_nico_guill_n.jpg",
        "transfermarkt",
    ),
    "b8d9cf54-1f84-43f7-a23a-6080410b22c3": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793656468/players/wonderkids/wk_b8d9cf54_noa_ojea.jpg",
        "transfermarkt_cloudinary",
    ),
    "7d59cfc2-8004-4691-97d6-100c3f119851": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784995915/generated-media/regen_newgen_faces/script_skin_hair/Mixed/Dark%20Brown/africa-darkbrown-62.png",
        "gtex_regen_newgen_face_bank",
    ),
    "0b2569f6-4e28-40eb-aab8-dbdba430c02e": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784995939/generated-media/regen_newgen_faces/script_skin_hair/Mixed/Light%20Brown/africa-lightbrown-112.png",
        "gtex_regen_newgen_face_bank",
    ),
    "6d07359b-3304-435a-ac12-de799dd94edc": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784995930/generated-media/regen_newgen_faces/script_skin_hair/Mixed/Dark%20Brown/africa-darkbrown-92.png",
        "gtex_regen_newgen_face_bank",
    ),
    "4fbfe030-42db-4d0c-aa96-2dbc6ea30339": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793656457/players/wonderkids/wk_4fbfe030_polli.jpg",
        "transfermarkt_cloudinary",
    ),
    "cc472489-3c8c-4d6f-8fe5-f8a3f834e528": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657557/players/wonderkids/wk_cc472489_rafael_lobato.jpg",
        "transfermarkt",
    ),
    "4cf4ccc7-c89e-4b91-a6f0-e5ca88bcb9b0": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657531/players/wonderkids/wk_4cf4ccc7_rapha_l_le_guen.jpg",
        "transfermarkt",
    ),
    "5b60fe1a-8708-410b-8f3b-997252e7d115": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793656513/players/wonderkids/wk_5b60fe1a_rayan_atikallah.png",
        "wikimedia_cloudinary",
    ),
    "bc5fc2bb-3c6e-42fe-9103-3ba70577edd1": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793656320/players/wonderkids/wk_bc5fc2bb_rayane_messi.png",
        "sofifa_cloudinary",
    ),
    "f0d74fc5-67c2-43a4-bf14-f5b405729745": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657554/players/wonderkids/wk_f0d74fc5_riquelme_felipe.jpg",
        "transfermarkt",
    ),
    "ae1a317b-8106-48b9-8b25-2cedaf8bfe38": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784995895/generated-media/regen_newgen_faces/script_skin_hair/Mixed/Dark%20Brown/africa-darkbrown-243.png",
        "gtex_regen_newgen_face_bank",
    ),
    "68b0daed-e6ce-4382-8725-f5fe0c3bab64": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657558/players/wonderkids/wk_68b0daed_salim_laghzaoui.jpg",
        "transfermarkt",
    ),
    "2b9644e8-6701-4eb1-b3bd-a17618ad2d2a": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793656471/players/wonderkids/wk_2b9644e8_samuel_mart_nez.jpg",
        "transfermarkt_cloudinary",
    ),
    "f51aecba-cc72-441d-85dd-52a0ca112a3a": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784995982/generated-media/regen_newgen_faces/script_skin_hair/Mixed/Light%20Brown/africa-lightbrown-206.png",
        "gtex_regen_newgen_face_bank",
    ),
    "3dc85071-ea05-4fda-af73-3773a7aa2da6": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793656477/players/wonderkids/wk_3dc85071_santiago_londo_o.png",
        "transfermarkt_cloudinary",
    ),
    "3198f542-7c33-4746-b14a-af2ac86849ed": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657565/players/wonderkids/wk_3198f542_simone_lontani.jpg",
        "transfermarkt",
    ),
    "96c12838-76e8-472c-8441-5665a5a66f8c": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793656321/players/wonderkids/wk_96c12838_sule.png",
        "sofifa_cloudinary",
    ),
    "bb6861a2-6303-489e-b7e7-7b1419195f99": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793656448/players/wonderkids/wk_bb6861a2_teo_hupfauf.png",
        "transfermarkt_cloudinary",
    ),
    "b14f9f17-0440-4e96-b414-02f69f16bc36": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784995852/generated-media/regen_newgen_faces/script_skin_hair/Mixed/Dark%20Brown/africa-darkbrown-15.png",
        "gtex_regen_newgen_face_bank",
    ),
    "d55ae595-4384-4af2-aa40-6cc902bf7396": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657553/players/wonderkids/wk_d55ae595_tiago_andrade.jpg",
        "transfermarkt",
    ),
    "c953e6c5-2b62-48fd-92a0-ff2d360ec2e8": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657559/players/wonderkids/wk_c953e6c5_tiago_poller.jpg",
        "transfermarkt",
    ),
    "a9554acc-17d5-46cb-b9c5-ca24e41747fa": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784995826/generated-media/regen_newgen_faces/script_skin_hair/Mixed/Blonde/africa-blonde-6.png",
        "gtex_regen_newgen_face_bank",
    ),
    "ee3caac7-64c6-47fa-a58c-e5c7e52aaa0a": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657539/players/wonderkids/wk_ee3caac7_tommy_marqu_s.jpg",
        "transfermarkt",
    ),
    "a2b9d78f-11ba-4ec8-bccc-a197830f2b96": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793656317/players/wonderkids/wk_a2b9d78f_tycho_de_wit.png",
        "sofifa_cloudinary",
    ),
    "659ad39f-0537-4d06-b5b8-1165cfaae380": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784995788/generated-media/regen_newgen_faces/script_skin_hair/Mixed/Black/africa-black-6.png",
        "gtex_regen_newgen_face_bank",
    ),
    "3fae2f10-926c-4fa7-81d7-03649f4faee0": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784995982/generated-media/regen_newgen_faces/script_skin_hair/Mixed/Light%20Brown/africa-lightbrown-206.png",
        "gtex_regen_newgen_face_bank",
    ),
    "1ba82227-abf9-46c9-b549-e01ff68ce177": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657546/players/wonderkids/wk_1ba82227_yanik_spalt.jpg",
        "transfermarkt",
    ),
    "7f1cd9da-1ed7-43c1-a010-40e898a2d50c": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657550/players/wonderkids/wk_7f1cd9da_yumeki_yokoyama.jpg",
        "transfermarkt",
    ),
    "573b21bf-e9e9-4111-8499-bf2c35e5785b": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784995775/generated-media/regen_newgen_faces/script_skin_hair/Mixed/Black/africa-black-248.png",
        "gtex_regen_newgen_face_bank",
    ),
    "498a94f9-943b-453a-bcd3-08998f2d41e7": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784995787/generated-media/regen_newgen_faces/script_skin_hair/Mixed/Black/africa-black-52.png",
        "gtex_regen_newgen_face_bank",
    ),
    "2473ad6f-c0ad-4d8e-bf94-7806d66a1fc6": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784995820/generated-media/regen_newgen_faces/script_skin_hair/Mixed/Blonde/africa-blonde-46.png",
        "gtex_regen_newgen_face_bank",
    ),
    "74f98132-fbad-4ae7-a98e-93bcf253b780": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657600/players/wonderkids/wk_74f98132_aleksander_wyganowski.jpg",
        "transfermarkt",
    ),
    "42099f7f-9375-4526-bcd9-f60b1685a456": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657583/players/wonderkids/wk_42099f7f_alexander_odefalk.jpg",
        "transfermarkt",
    ),
    "4c63ae7f-3695-40d5-80a4-41cc1e9e5b3e": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784995946/generated-media/regen_newgen_faces/script_skin_hair/Mixed/Light%20Brown/africa-lightbrown-122.png",
        "gtex_regen_newgen_face_bank",
    ),
    "754b7228-2894-4df4-a0c0-64070516e9fd": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657578/players/wonderkids/wk_754b7228_brad_manguelle.jpg",
        "transfermarkt",
    ),
    "730daa65-c18c-47cc-b65b-28b915d56340": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657580/players/wonderkids/wk_730daa65_bradley_burrowes.jpg",
        "transfermarkt",
    ),
    "0c016997-713c-4c54-ba2e-f3e3153c98c5": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793656551/players/wonderkids/wk_0c016997_breno_sales.png",
        "wikimedia_cloudinary",
    ),
    "be4653ac-aee3-4cdb-a9a0-2b9aea22c40c": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784995956/generated-media/regen_newgen_faces/script_skin_hair/Mixed/Light%20Brown/africa-lightbrown-144.png",
        "gtex_regen_newgen_face_bank",
    ),
    "cf1b2b99-8ca3-478e-aacd-5ea93c686e81": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657595/players/wonderkids/wk_cf1b2b99_caelan_cadamarteri.jpg",
        "transfermarkt",
    ),
    "c82922ab-b8bf-4203-9831-c3536e1eb3c3": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657612/players/wonderkids/wk_c82922ab_calvin_carrilho.jpg",
        "transfermarkt",
    ),
    "439a99c7-11cc-4ea9-83b8-7ce030ec7ff2": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784995982/generated-media/regen_newgen_faces/script_skin_hair/Mixed/Light%20Brown/africa-lightbrown-204.png",
        "gtex_regen_newgen_face_bank",
    ),
    "c21c1ef1-cc4f-405b-9b75-0b288519146d": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657595/players/wonderkids/wk_c21c1ef1_chizzy_ezenwata.jpg",
        "transfermarkt",
    ),
    "cce9bb48-28fd-4f4d-b9d9-6dade17c2437": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657578/players/wonderkids/wk_cce9bb48_cristian_samir_inda.jpg",
        "transfermarkt",
    ),
    "8b3915c5-bee3-4376-acf6-af0b13f80da8": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784996017/generated-media/regen_newgen_faces/script_skin_hair/Mixed/Light%20Brown/africa-lightbrown-67.png",
        "gtex_regen_newgen_face_bank",
    ),
    "a68881b3-33bc-41a7-b3ed-d08851463fc5": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657604/players/wonderkids/wk_a68881b3_david_boly.jpg",
        "transfermarkt",
    ),
    "5a412924-3ba2-446d-9ca5-67a399d7f7b5": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793659129/players/wonderkids/wk_5a412924_david_nogueira.webp",
        "transfermarkt_uploaded",
    ),
    "f61299f6-8505-4e6b-91eb-819a5fba9a8a": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657612/players/wonderkids/wk_f61299f6_destiny_elimoghale.jpg",
        "transfermarkt",
    ),
    "cc25f8a2-6058-4f4a-8019-c25c4849d275": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657600/players/wonderkids/wk_cc25f8a2_diego_minete.png",
        "transfermarkt",
    ),
    "b5ac7f07-952c-47e6-85cb-df5d4dfc5248": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657605/players/wonderkids/wk_b5ac7f07_diogo_coelho.png",
        "transfermarkt",
    ),
    "e036cde2-c697-456e-9d43-ace5860700f8": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657605/players/wonderkids/wk_e036cde2_djibril_ouziad.jpg",
        "transfermarkt",
    ),
    "42df1a17-5bcd-4a18-951c-426edefbc0d3": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784995873/generated-media/regen_newgen_faces/script_skin_hair/Mixed/Dark%20Brown/africa-darkbrown-202.png",
        "gtex_regen_newgen_face_bank",
    ),
    "4c25a797-38ae-49b8-9154-6877f77af14e": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657574/players/wonderkids/wk_4c25a797_dwight_ede_eriyo.jpg",
        "transfermarkt",
    ),
    "d63cb93f-9fb0-4fe8-8c1e-64d0155e8d0c": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784996016/generated-media/regen_newgen_faces/script_skin_hair/Mixed/Light%20Brown/africa-lightbrown-60.png",
        "gtex_regen_newgen_face_bank",
    ),
    "d258cef3-fa9a-4130-9e69-b7d15b5f9a62": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657585/players/wonderkids/wk_d258cef3_ebu_bekir_i.jpg",
        "transfermarkt",
    ),
    "72debd19-4326-43f0-81af-6d01fa540c57": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784995908/generated-media/regen_newgen_faces/script_skin_hair/Mixed/Dark%20Brown/africa-darkbrown-45.png",
        "gtex_regen_newgen_face_bank",
    ),
    "66261d21-943c-42be-abbf-4d5d786d473e": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657577/players/wonderkids/wk_66261d21_emilio_lawrence.jpg",
        "transfermarkt",
    ),
    "3a93127b-9aae-47f5-bef4-eeedc445c9d6": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793656323/players/wonderkids/wk_3a93127b_enzo_dos_santos.png",
        "sofifa_cloudinary",
    ),
    "13541076-a951-4778-9b06-2c9454841303": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793659130/players/wonderkids/wk_13541076_erik_farkas.webp",
        "transfermarkt_uploaded",
    ),
    "08837a19-afe5-4a48-b79f-c5f7f0b6cfd1": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657604/players/wonderkids/wk_08837a19_essien_bassey.jpg",
        "transfermarkt",
    ),
    "bb05673b-6cdc-4b70-8a94-726728cd5d6b": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657591/players/wonderkids/wk_bb05673b_freddie_simmonds.jpg",
        "transfermarkt",
    ),
    "88b6668b-dca3-4346-b449-d013cf875595": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793656550/players/wonderkids/wk_88b6668b_gabriel__ndio.jpg",
        "wikimedia_cloudinary",
    ),
    "59a9c53d-160f-4fd2-a4c7-2be8de3770a8": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793656323/players/wonderkids/wk_59a9c53d_gera_n_van_loon.png",
        "sofifa_cloudinary",
    ),
    "8bf1c84d-1b4a-4d27-ad61-e3118cd81fbf": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657590/players/wonderkids/wk_8bf1c84d_gianluca_okon_engstler.jpg",
        "transfermarkt",
    ),
    "d843c3f4-b84c-4e88-bada-7461f9594df0": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657616/players/wonderkids/wk_d843c3f4_giuseppe_pipit.jpg",
        "transfermarkt",
    ),
    "67330e7f-39de-4bf8-aedd-2bc55e5abe7c": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784995983/generated-media/regen_newgen_faces/script_skin_hair/Mixed/Light%20Brown/africa-lightbrown-205.png",
        "gtex_regen_newgen_face_bank",
    ),
    "d4ce870f-a82e-43d8-b8f4-ec33ba5ea494": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657590/players/wonderkids/wk_d4ce870f_halam_loboa.jpg",
        "transfermarkt",
    ),
    "ce173e6b-642b-49ae-ad3f-36c87b89b5ca": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657583/players/wonderkids/wk_ce173e6b_hezekiah_grimwade.jpg",
        "transfermarkt",
    ),
    "11cf3311-cc56-40b8-8d75-b4c4a15fb113": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657580/players/wonderkids/wk_11cf3311_holger_quintero.jpg",
        "transfermarkt",
    ),
    "3e436491-02d2-4ba6-8983-6fac2a1bac6c": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657611/players/wonderkids/wk_3e436491_holmes_j_nior.jpg",
        "transfermarkt",
    ),
    "1651801a-e5bf-4ccf-b7ee-a98f6fe8fa4e": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784995980/generated-media/regen_newgen_faces/script_skin_hair/Mixed/Light%20Brown/africa-lightbrown-2.png",
        "gtex_regen_newgen_face_bank",
    ),
    "f3301677-d0fe-466b-a38e-184ed929babe": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657591/players/wonderkids/wk_f3301677_ifeanyichukwu_onwuzulike.jpg",
        "transfermarkt",
    ),
    "ac567646-d05c-4e72-915e-243365321226": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657569/players/wonderkids/wk_ac567646_ilai_grootfaam.jpg",
        "transfermarkt",
    ),
    "225800bd-c8fb-4c34-a60d-9e4d5fdbba9e": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657612/players/wonderkids/wk_225800bd_jaden_umeh.jpg",
        "transfermarkt",
    ),
    "f23c0629-0aba-4349-9152-04a8ce0b03d2": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793656324/players/wonderkids/wk_f23c0629_jakob_sch_ller.png",
        "sofifa_cloudinary",
    ),
    "997f3146-bce2-424e-9a33-b2cd332602ec": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657572/players/wonderkids/wk_997f3146_jerayno_schaken.jpg",
        "transfermarkt",
    ),
    "96a102c2-d469-42b9-924a-d6d3581b71e0": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784995794/generated-media/regen_newgen_faces/script_skin_hair/Mixed/Black/africa-black-75.png",
        "gtex_regen_newgen_face_bank",
    ),
    "a52552c5-880c-412e-aebb-99cdb5db7046": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657572/players/wonderkids/wk_a52552c5_jerome_diallo.jpg",
        "transfermarkt",
    ),
    "747b824c-669b-49e5-869a-b5bddf53203b": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793659132/players/wonderkids/wk_747b824c_joao_bezerra.webp",
        "transfermarkt_uploaded",
    ),
    "f594c295-722d-482c-9664-8ba3f84e147f": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657614/players/wonderkids/wk_f594c295_jo_l_drakes_thomas.jpg",
        "transfermarkt",
    ),
    "a30222f6-f8aa-4209-8b65-45c3c7932cd0": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657572/players/wonderkids/wk_a30222f6_johan_mart_nez.jpg",
        "transfermarkt",
    ),
    "a233fc7e-f8fc-43c6-b462-ce5e999f87fb": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784995873/generated-media/regen_newgen_faces/script_skin_hair/Mixed/Dark%20Brown/africa-darkbrown-200.png",
        "gtex_regen_newgen_face_bank",
    ),
    "848080a0-7a82-4c4e-8a32-bc832266aaa9": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784995881/generated-media/regen_newgen_faces/script_skin_hair/Mixed/Dark%20Brown/africa-darkbrown-217.png",
        "gtex_regen_newgen_face_bank",
    ),
    "5644d5fc-d33d-4ef3-ad6a-3874aadd4929": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657606/players/wonderkids/wk_5644d5fc_joseph_opoku.jpg",
        "transfermarkt",
    ),
    "d37480c7-7d56-4ecc-a0a7-29198c2b4a5a": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784995978/generated-media/regen_newgen_faces/script_skin_hair/Mixed/Light%20Brown/africa-lightbrown-196.png",
        "gtex_regen_newgen_face_bank",
    ),
    "b68b87d2-55ab-4b09-9b46-c1eb991b186c": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657614/players/wonderkids/wk_b68b87d2_kau__furquim.png",
        "transfermarkt",
    ),
    "01f2b2ec-0a21-461f-922c-002b898e179a": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784995923/generated-media/regen_newgen_faces/script_skin_hair/Mixed/Dark%20Brown/africa-darkbrown-75.png",
        "gtex_regen_newgen_face_bank",
    ),
    "3d04a994-541e-4bc7-b64b-be72cf444883": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657585/players/wonderkids/wk_3d04a994_leon_westin.jpg",
        "transfermarkt",
    ),
    "1f56ae51-ce65-4883-9292-7d0b9a2248c6": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784996009/generated-media/regen_newgen_faces/script_skin_hair/Mixed/Light%20Brown/africa-lightbrown-42.png",
        "gtex_regen_newgen_face_bank",
    ),
    "1f84d2bc-f1cc-4421-81b6-ab5874c02e8b": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784995779/generated-media/regen_newgen_faces/script_skin_hair/Mixed/Black/africa-black-32.png",
        "gtex_regen_newgen_face_bank",
    ),
    "2f3924d5-13c7-44ef-8f66-405a3b59a5d4": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657599/players/wonderkids/wk_2f3924d5_loukman_tapsoba.jpg",
        "transfermarkt",
    ),
    "c3bb7397-157e-40a4-a77d-40551686714c": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784995774/generated-media/regen_newgen_faces/script_skin_hair/Mixed/Black/africa-black-244.png",
        "gtex_regen_newgen_face_bank",
    ),
    "de2e02be-74ee-440b-b138-1ea4babbb11b": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657601/players/wonderkids/wk_de2e02be_luke_fahrenhorst.jpg",
        "transfermarkt",
    ),
    "cc74dfdd-b246-4292-b8f5-82be9810ab89": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784995873/generated-media/regen_newgen_faces/script_skin_hair/Mixed/Dark%20Brown/africa-darkbrown-202.png",
        "gtex_regen_newgen_face_bank",
    ),
    "feb344ca-bc3b-45b6-b055-32c606f75a5c": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657582/players/wonderkids/wk_feb344ca_marcos_ort_z.jpg",
        "transfermarkt",
    ),
    "0a77f4cc-631e-4679-8523-84bec6c511e5": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657583/players/wonderkids/wk_0a77f4cc_matteo_mari.jpg",
        "transfermarkt",
    ),
    "687fa3ea-1908-45c1-a6f2-3daf8ecf756c": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657605/players/wonderkids/wk_687fa3ea_mayson_grothe.jpg",
        "transfermarkt",
    ),
    "05af5ad7-2627-4bd6-ba12-877e7afeb9a4": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657587/players/wonderkids/wk_05af5ad7_miguel_ag_mez.jpg",
        "transfermarkt",
    ),
    "284399e5-951b-433d-9cb7-c748e0556086": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657588/players/wonderkids/wk_284399e5_miguel_figueiredo.jpg",
        "transfermarkt",
    ),
    "0d686a37-b905-4587-834d-6cbd2888715c": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657585/players/wonderkids/wk_0d686a37_miha_matja_ec.jpg",
        "transfermarkt",
    ),
    "089ddd9a-91d5-4b08-8da0-671793d543dd": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657577/players/wonderkids/wk_089ddd9a_mo_missanga.jpg",
        "transfermarkt",
    ),
    "fd223784-d3c8-4a41-95da-b08e796274d7": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657613/players/wonderkids/wk_fd223784_nik__kafar__u_i.png",
        "transfermarkt",
    ),
    "16e2459e-4d87-4b15-b104-b73ddb30a4bb": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657572/players/wonderkids/wk_16e2459e_noah_ajayi.jpg",
        "transfermarkt",
    ),
    "b58ef121-5f58-44bb-adc7-c227eda9b857": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784996028/generated-media/regen_newgen_faces/script_skin_hair/Mixed/Light%20Brown/africa-lightbrown-90.png",
        "gtex_regen_newgen_face_bank",
    ),
    "041c2250-5711-4ab8-90b4-8996fd4a6452": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657601/players/wonderkids/wk_041c2250_oliver_m_nsson.jpg",
        "transfermarkt",
    ),
    "bcb2e40f-ec2d-4c83-81cf-01a773343c8c": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657613/players/wonderkids/wk_bcb2e40f_owen_emeka.png",
        "transfermarkt",
    ),
    "d2d04a09-f8e7-49f4-80a3-3ef4db5e588c": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784995799/generated-media/regen_newgen_faces/script_skin_hair/Mixed/Black/africa-black-8.png",
        "gtex_regen_newgen_face_bank",
    ),
    "acc940c7-1167-4daf-b665-de8a79c781b3": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657575/players/wonderkids/wk_acc940c7_ramon_rique.jpg",
        "transfermarkt",
    ),
    "d4c57e10-651a-4976-93b5-665a8978b328": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657589/players/wonderkids/wk_d4c57e10_reggie_watson.jpg",
        "transfermarkt",
    ),
    "8cb32b57-156f-4e99-8eeb-81ed33963096": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784995719/generated-media/regen_newgen_faces/script_skin_hair/Mixed/Black/africa-black-107.png",
        "gtex_regen_newgen_face_bank",
    ),
    "1c7874ea-dd12-4081-8a71-16f269effe4b": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784995972/generated-media/regen_newgen_faces/script_skin_hair/Mixed/Light%20Brown/africa-lightbrown-182.png",
        "gtex_regen_newgen_face_bank",
    ),
    "ee1642f2-84c6-45ec-b51d-54020c32c55b": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784995852/generated-media/regen_newgen_faces/script_skin_hair/Mixed/Dark%20Brown/africa-darkbrown-147.png",
        "gtex_regen_newgen_face_bank",
    ),
    "1a3f41c9-d044-4d92-857f-80e093467fe7": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657600/players/wonderkids/wk_1a3f41c9_sebastian_pech.jpg",
        "transfermarkt",
    ),
    "f4007a1d-cf5d-4383-abe6-3fbb497d1837": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657582/players/wonderkids/wk_f4007a1d_seth_ridgeon.jpg",
        "transfermarkt",
    ),
    "ba7f90fb-9b36-4d98-abd7-b0b458a692d5": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657601/players/wonderkids/wk_ba7f90fb_sfiso_timba.jpg",
        "transfermarkt",
    ),
    "de78bd58-7e8d-498d-b31b-ca4f64d8e767": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657613/players/wonderkids/wk_de78bd58_shola_jimoh.jpg",
        "transfermarkt",
    ),
    "590d5a13-c151-483b-8578-dc4672847c57": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657606/players/wonderkids/wk_590d5a13_sim_n_escobar.jpg",
        "transfermarkt",
    ),
    "8c0e7886-f8ce-4522-b161-4379325a4423": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784996024/generated-media/regen_newgen_faces/script_skin_hair/Mixed/Light%20Brown/africa-lightbrown-86.png",
        "gtex_regen_newgen_face_bank",
    ),
    "a9f2ad2a-76d9-42a5-a64d-08c948a501a2": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784995809/generated-media/regen_newgen_faces/script_skin_hair/Mixed/Blonde/africa-blonde-20.png",
        "gtex_regen_newgen_face_bank",
    ),
    "47c0e82a-2f67-49c2-82b3-4d582acd0353": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784995846/generated-media/regen_newgen_faces/script_skin_hair/Mixed/Dark%20Brown/africa-darkbrown-136.png",
        "gtex_regen_newgen_face_bank",
    ),
    "28ad96bc-4f22-4619-ae9f-5295a135e0c4": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657597/players/wonderkids/wk_28ad96bc_tim_t_farkas.jpg",
        "transfermarkt",
    ),
    "6bf27a70-5383-4667-b807-5c3fca45d0a1": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784995969/generated-media/regen_newgen_faces/script_skin_hair/Mixed/Light%20Brown/africa-lightbrown-172.png",
        "gtex_regen_newgen_face_bank",
    ),
    "93aba66e-1116-4dfc-bbba-cbc7660fd44c": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784995727/generated-media/regen_newgen_faces/script_skin_hair/Mixed/Black/africa-black-13.png",
        "gtex_regen_newgen_face_bank",
    ),
    "bc01d1c8-9c85-45e5-8643-1cb85e5a60ee": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784995819/generated-media/regen_newgen_faces/script_skin_hair/Mixed/Blonde/africa-blonde-40.png",
        "gtex_regen_newgen_face_bank",
    ),
    "8beb669d-665c-4619-8b78-9049f06bc842": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784995956/generated-media/regen_newgen_faces/script_skin_hair/Mixed/Light%20Brown/africa-lightbrown-142.png",
        "gtex_regen_newgen_face_bank",
    ),
    "dc5e7e0e-7f7f-40f2-a2bc-0f5f25d7c926": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784995997/generated-media/regen_newgen_faces/script_skin_hair/Mixed/Light%20Brown/africa-lightbrown-239.png",
        "gtex_regen_newgen_face_bank",
    ),
    "de561135-b08b-40b9-99f2-b162c7eb9c40": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793656324/players/wonderkids/wk_de561135_vincent_joseph.png",
        "sofifa_cloudinary",
    ),
    "b1154e57-5272-4851-8957-4c6ac455accd": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784995774/generated-media/regen_newgen_faces/script_skin_hair/Mixed/Black/africa-black-245.png",
        "gtex_regen_newgen_face_bank",
    ),
    "df6df01e-1009-4ce1-8584-fc9e356ccf30": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657584/players/wonderkids/wk_df6df01e_wassim_slama.jpg",
        "transfermarkt",
    ),
    "c715064c-cadf-4300-8e84-f3d7ea080a89": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784995734/generated-media/regen_newgen_faces/script_skin_hair/Mixed/Black/africa-black-145.png",
        "gtex_regen_newgen_face_bank",
    ),
    "d6d91472-ad30-4e47-9bda-8d2376547422": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657578/players/wonderkids/wk_d6d91472_zinedine_zidane_bedoya.jpg",
        "transfermarkt",
    ),
    "bc79bd19-452f-4ccf-95c4-386f02f2f443": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784996029/generated-media/regen_newgen_faces/script_skin_hair/Mixed/Light%20Brown/africa-lightbrown-91.png",
        "gtex_regen_newgen_face_bank",
    ),
    "5455dad9-9f12-4a07-a16a-3a57c14a6076": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657620/players/wonderkids/wk_5455dad9_christian_imga.jpg",
        "transfermarkt",
    ),
    "d99ba03b-9f77-42be-af13-de641445218b": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657620/players/wonderkids/wk_d99ba03b_emmanuel_fejokwu.jpg",
        "transfermarkt",
    ),
    "f7050006-602c-4a56-8f47-aae0ace39d0f": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784995747/generated-media/regen_newgen_faces/script_skin_hair/Mixed/Black/africa-black-177.png",
        "gtex_regen_newgen_face_bank",
    ),
    "ab5553a5-147d-4f4a-b602-2dc5822064d0": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793659131/players/wonderkids/wk_ab5553a5_isaac_badu.webp",
        "transfermarkt_uploaded",
    ),
    "763fdc5d-20ea-49b1-8330-c818858ad3e3": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784995721/generated-media/regen_newgen_faces/script_skin_hair/Mixed/Black/africa-black-116.png",
        "gtex_regen_newgen_face_bank",
    ),
    "513936d3-527d-4b4d-905d-3b92a78891c2": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657623/players/wonderkids/wk_513936d3_jeshurun_simeon.jpg",
        "transfermarkt",
    ),
    "d50e66b6-4ead-4347-87de-75b965ab345c": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657618/players/wonderkids/wk_d50e66b6_jorge_dom_nguez.jpg",
        "transfermarkt",
    ),
    "be546771-3f03-44f2-a28c-b0cbe5836f37": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657622/players/wonderkids/wk_be546771_ludovico_varali.jpg",
        "transfermarkt",
    ),
    "2a0ee3bb-bdc7-45fb-bb33-75d4d648eab2": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657616/players/wonderkids/wk_2a0ee3bb_luis_maturana.jpg",
        "transfermarkt",
    ),
    "42d14563-da24-4335-a72c-3b37c160611f": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784995859/generated-media/regen_newgen_faces/script_skin_hair/Mixed/Dark%20Brown/africa-darkbrown-164.png",
        "gtex_regen_newgen_face_bank",
    ),
    "2010b407-5e93-4621-bfa0-82d564a97dd4": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784995854/generated-media/regen_newgen_faces/script_skin_hair/Mixed/Dark%20Brown/africa-darkbrown-156.png",
        "gtex_regen_newgen_face_bank",
    ),
    "a001a036-17ec-497e-b0b0-195e25873d24": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657624/players/wonderkids/wk_a001a036_maxima_goffi.jpg",
        "transfermarkt",
    ),
    "9b03e002-d04e-4ddc-8fa2-9e652f1fd085": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657618/players/wonderkids/wk_9b03e002_shota_kofie.jpg",
        "transfermarkt",
    ),
    "d6a720c9-babc-4218-9b7a-6325bd50e2dc": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784995813/generated-media/regen_newgen_faces/script_skin_hair/Mixed/Blonde/africa-blonde-24.png",
        "gtex_regen_newgen_face_bank",
    ),
    "347e4176-3eb0-4d61-ad5b-34f0be0e7602": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784995779/generated-media/regen_newgen_faces/script_skin_hair/Mixed/Black/africa-black-31.png",
        "gtex_regen_newgen_face_bank",
    ),
    "3e4a1fbe-5c70-4610-a1ee-3ed3639549ba": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784995734/generated-media/regen_newgen_faces/script_skin_hair/Mixed/Black/africa-black-148.png",
        "gtex_regen_newgen_face_bank",
    ),
    "7ed0d4af-53de-4c5d-947b-f5df859ec89b": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793656329/players/wonderkids/wk_7ed0d4af_aar_n_mart_n.png",
        "sofifa_cloudinary",
    ),
    "60285a2a-fc32-4ce4-974d-72cb70ea2250": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/Hispanic/Dark Brown/Untitled-23 copy.png",
        "gtex_regen_newgen_face_bank",
    ),
    "4e3ec46e-27ac-4da9-b6bb-3e382f0c6a2d": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657774/players/wonderkids/wk_4e3ec46e_abdenour_barkat.jpg",
        "transfermarkt",
    ),
    "da454649-3ed9-4ed9-a49f-ab8002d53a33": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657835/players/wonderkids/wk_da454649_abderrahmane_bekkour.jpg",
        "transfermarkt",
    ),
    "076b621e-07b7-4f21-823e-5444c4882d17": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657716/players/wonderkids/wk_076b621e_abdou_kemo_badji.jpg",
        "transfermarkt",
    ),
    "9b607b18-96de-4348-a046-2ea03d90ba99": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657656/players/wonderkids/wk_9b607b18_abdoulaye_nassoko.jpg",
        "transfermarkt",
    ),
    "87efd7e2-723c-49ba-9fcf-532cd485e8ba": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657850/players/wonderkids/wk_87efd7e2_abdoulie_kah.png",
        "transfermarkt",
    ),
    "fc4cb742-9356-42ee-97ce-d7bf32f86e69": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793658405/players/wonderkids/wk_fc4cb742_abdul_aziz_issah.jpg",
        "migrated_to_cloudinary",
    ),
    "cb5d8783-d60b-4df1-80af-c2d2aa0446bd": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793658405/players/wonderkids/wk_cb5d8783_abdul_aziz_issah.jpg",
        "migrated_to_cloudinary",
    ),
    "2eedc3ef-89f2-4aaf-a73d-cdc508e83668": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657802/players/wonderkids/wk_2eedc3ef_abdullahi_umar.png",
        "transfermarkt",
    ),
    "e1dc2c13-4427-41cc-849a-a1eff58a2ca2": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657764/players/wonderkids/wk_e1dc2c13_abdulrasheed_shehu_dabai.png",
        "transfermarkt",
    ),
    "ea26dee9-43f0-4f20-a53b-219d71acda2d": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/African/Dark Brown/africa-darkbrown-208.png",
        "gtex_regen_newgen_face_bank",
    ),
    "270ac7c3-22f3-4851-aaa0-175742e53bb7": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784998228/generated-media/regen_newgen_faces/script_skin_hair/African/Light%20Brown/africa-lightbrown-55.png",
        "gtex_regen_newgen_face_bank",
    ),
    "b48192b3-f4ca-4912-9d35-352725282f57": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657841/players/wonderkids/wk_b48192b3_achref_abada.jpg",
        "transfermarkt",
    ),
    "0f3a7cda-810b-4407-ac48-cdfb08a9117f": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/South european/Dark Brown/271.png",
        "gtex_regen_newgen_face_bank",
    ),
    "1e2ad57e-fbce-4127-b3ba-4bea38e7a3f3": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657645/players/wonderkids/wk_1e2ad57e_adam_ayari.jpg",
        "transfermarkt",
    ),
    "0d0ba0d0-46db-4b19-a072-9f60c6583256": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657656/players/wonderkids/wk_0d0ba0d0_adam_el_chaar.jpg",
        "transfermarkt",
    ),
    "e860dbfd-87b9-4282-9e09-893562466e2f": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/North european/Dark Brown/Untitled-179 copy.png",
        "gtex_regen_newgen_face_bank",
    ),
    "ba9b042f-f467-412a-a742-658cb6a209d3": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/North european/Dark Brown/Untitled-153 copy.png",
        "gtex_regen_newgen_face_bank",
    ),
    "a1a78d1b-d3c0-48d2-8122-7acf47db8225": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657892/players/wonderkids/wk_a1a78d1b_adam_nosel.jpg",
        "transfermarkt",
    ),
    "14fbc935-2cce-40f8-add9-8cc668923c85": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657736/players/wonderkids/wk_14fbc935_adama_baradji.png",
        "transfermarkt",
    ),
    "6dd6f96a-3caf-4531-a8bd-c5f1e1464ab0": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657804/players/wonderkids/wk_6dd6f96a_adama_coulibaly.jpg",
        "transfermarkt",
    ),
    "3c6bca18-17aa-4805-8122-48f7388fc115": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657773/players/wonderkids/wk_3c6bca18_aderemi_adeoye.jpg",
        "transfermarkt",
    ),
    "4c8bf66d-dbc8-4ebf-84c3-858875c9388d": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657683/players/wonderkids/wk_4c8bf66d_adil_hamdani.jpg",
        "transfermarkt",
    ),
    "0d93ad5f-0f1e-478f-9223-6305d043a329": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657891/players/wonderkids/wk_0d93ad5f_adrian_lis.jpg",
        "transfermarkt",
    ),
    "016b5d53-4329-4063-ae45-dc2bbfdfc869": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793658396/players/wonderkids/wk_016b5d53_adri_n_liso.png",
        "migrated_to_cloudinary",
    ),
    "0d7b442c-3abe-4cca-853e-bb6e442902d7": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793656342/players/wonderkids/wk_0d7b442c_adri_n_p_rez.png",
        "sofifa_cloudinary",
    ),
    "09763eb0-5d93-4553-8d31-ce51908594b1": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/Hispanic/Dark Brown/386.png",
        "gtex_regen_newgen_face_bank",
    ),
    "73cf01a3-2497-4bc8-9b2c-fd4d9cbf2bc1": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793656202/players/wonderkids/wk_73cf01a3_agust_n_mart_nez.png",
        "sofifa_cloudinary",
    ),
    "0dadb962-b5e6-49cd-924c-48217a870a8d": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793656184/players/wonderkids/wk_0dadb962_agust_n_mart_nez.png",
        "sofifa_cloudinary",
    ),
    "36a71abe-6c20-4661-bc2c-16143dba334b": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657780/players/wonderkids/wk_36a71abe_akiles.png",
        "transfermarkt",
    ),
    "8148c141-02a1-4de5-81c0-aa346f2cea05": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657778/players/wonderkids/wk_8148c141_alber_castelau.jpg",
        "transfermarkt",
    ),
    "5eade44e-119e-40ce-a887-d10f6f5eb759": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657741/players/wonderkids/wk_5eade44e_albert_navarro.jpg",
        "transfermarkt",
    ),
    "721b88f2-d55d-4ef6-88da-01498bd1c7d0": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/North european/Dark Brown/568.png",
        "gtex_regen_newgen_face_bank",
    ),
    "a0945ae7-cab7-474a-9d68-8cd1179e8d30": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793658407/players/wonderkids/wk_a0945ae7_alejandro_gomes_rodriguez.png",
        "migrated_to_cloudinary",
    ),
    "50df4978-e1db-40f1-a564-21c37c160a04": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/South european/Dark Brown/843.png",
        "gtex_regen_newgen_face_bank",
    ),
    "ae19f42a-401e-428e-a0a5-c5b16308b743": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657700/players/wonderkids/wk_ae19f42a_alessandro_crimaldi.jpg",
        "transfermarkt",
    ),
    "81f2d327-3d24-4afc-8c61-6a00ff82609e": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657843/players/wonderkids/wk_81f2d327_alessandro_gaul_souza.jpg",
        "transfermarkt",
    ),
    "64a0ce8c-ddad-450a-b543-5e27fc56d2df": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793658406/players/wonderkids/wk_64a0ce8c_alessandro_longoni.jpg",
        "migrated_to_cloudinary",
    ),
    "64eba286-6492-4869-a945-db20b16cb108": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657720/players/wonderkids/wk_64eba286_lex_marchal.jpg",
        "transfermarkt",
    ),
    "96ba9749-9f31-4f83-8353-16a8d2fa5359": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/Mixed/Dark Brown/africa-darkbrown-183.png",
        "gtex_regen_newgen_face_bank",
    ),
    "9cafb0a1-8e59-4985-a6b7-21e055b3fa23": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657799/players/wonderkids/wk_9cafb0a1_alex_ver_n.jpg",
        "transfermarkt",
    ),
    "a6516717-ff75-447c-ae15-eda057dcc328": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657823/players/wonderkids/wk_a6516717_alex_ver_n.jpg",
        "transfermarkt",
    ),
    "abd160d2-bcb3-464c-a89b-db64ab1c4795": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657779/players/wonderkids/wk_abd160d2_alex_woiski.png",
        "transfermarkt",
    ),
    "7cace80a-cb46-4c8b-b665-dc970d41efa2": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657908/players/wonderkids/wk_7cace80a_alexander_coenen.png",
        "transfermarkt",
    ),
    "41305ee8-2b3b-4c6f-9b9c-0c287a6190b6": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793658409/players/wonderkids/wk_41305ee8_alexander_legendre.png",
        "migrated_to_cloudinary",
    ),
    "5f4ea530-0c1f-4329-aaf2-4918264473f5": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657642/players/wonderkids/wk_5f4ea530_alexander_staff.jpg",
        "transfermarkt",
    ),
    "e3b721e8-2d2a-4f41-b0e3-3fd40273298c": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657792/players/wonderkids/wk_e3b721e8_alexander_staff.jpg",
        "transfermarkt",
    ),
    "47cd4dd5-4cd2-4ed1-a946-5793b35be331": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657881/players/wonderkids/wk_47cd4dd5_alexandru_stoian.png",
        "transfermarkt",
    ),
    "97a242d2-0cb8-436b-ad4f-502dc7b81d05": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/Hispanic/Dark Brown/682.png",
        "gtex_regen_newgen_face_bank",
    ),
    "45d7aada-7659-4611-b631-3f77f1a3e21d": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793658413/players/wonderkids/wk_45d7aada_alexis_vossah.png",
        "migrated_to_cloudinary",
    ),
    "3e2979ed-81fb-4bd3-b0e0-79e8e0208a5c": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/South european/Dark Brown/1032.png",
        "gtex_regen_newgen_face_bank",
    ),
    "4eb8d611-67e0-4941-81ea-1ab33ab4fe5c": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793656336/players/wonderkids/wk_4eb8d611_lvaro_vega_garc_a.png",
        "sofifa_cloudinary",
    ),
    "9559b8cd-1a30-4c8a-9acd-73eeb0953eae": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657814/players/wonderkids/wk_9559b8cd_amadou_ciss.png",
        "transfermarkt",
    ),
    "6f0b4701-6651-49df-ab7f-55848367f83d": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657812/players/wonderkids/wk_6f0b4701_amara_diouf.jpg",
        "transfermarkt",
    ),
    "d9c90743-c7c2-4c24-aa74-af9b32cf524b": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793656348/players/wonderkids/wk_d9c90743_amidou_doumbouya.png",
        "sofifa_cloudinary",
    ),
    "4bfa650b-81a8-488d-8f93-66f4861183ee": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/South european/Dark Brown/1040.png",
        "gtex_regen_newgen_face_bank",
    ),
    "b0f6a8bf-cbf8-421c-815c-a6726e8618c0": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/Middle east/Dark Brown/Untitled-56 copy.png",
        "gtex_regen_newgen_face_bank",
    ),
    "73dbe1ec-1bcc-401d-95cd-b4112be8df22": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/South european/Dark Brown/1129.png",
        "gtex_regen_newgen_face_bank",
    ),
    "bd286129-681f-40a8-a4bb-3a2e84caec57": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657787/players/wonderkids/wk_bd286129_andre_harriman_annous.jpg",
        "transfermarkt",
    ),
    "84441a5a-db80-414c-af2c-3d44d244829a": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/Mixed/Dark Brown/africa-darkbrown-217.png",
        "gtex_regen_newgen_face_bank",
    ),
    "a9f91082-bbf4-455d-b2a3-20dd93db8bf2": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/African/Dark Brown/africa-darkbrown-78.png",
        "gtex_regen_newgen_face_bank",
    ),
    "f40d6fac-4736-4fe6-b10c-7edcbb379e66": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657669/players/wonderkids/wk_f40d6fac_andy_marshall.jpg",
        "transfermarkt",
    ),
    "decd1994-1bed-49d3-89a0-a30bbf6005c4": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657861/players/wonderkids/wk_decd1994_angelo_candido.jpg",
        "transfermarkt",
    ),
    "3846a333-4b61-4e74-a85b-d143d13b2706": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793656330/players/wonderkids/wk_3846a333_antonio_g_mez.png",
        "sofifa_cloudinary",
    ),
    "52a7fd4d-4e01-410e-921f-efafe0d21457": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/Mixed/Dark Brown/africa-darkbrown-5.png",
        "gtex_regen_newgen_face_bank",
    ),
    "752c5182-203b-41f4-83ae-3bfadf9c6078": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657789/players/wonderkids/wk_752c5182_aristide_hentcho_nseke.jpg",
        "transfermarkt",
    ),
    "cced913d-3709-4a5e-b532-eda349832965": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793658402/players/wonderkids/wk_cced913d_arone_gadou.png",
        "migrated_to_cloudinary",
    ),
    "f3f58dd1-c3a8-4c31-b96f-f915878c33b8": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657882/players/wonderkids/wk_f3f58dd1_artem_rybak.png",
        "transfermarkt",
    ),
    "8889edaf-7750-482c-879a-91f65dc336ef": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793656213/players/wonderkids/wk_8889edaf_arthur_henrique.png",
        "sofifa_cloudinary",
    ),
    "4bc089cc-869b-4461-9335-74b667ce4711": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657740/players/wonderkids/wk_4bc089cc_asier_bonel.jpg",
        "transfermarkt",
    ),
    "8a164c06-8398-4c16-af8c-3c1931cb0d16": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/South european/Dark Brown/887.png",
        "gtex_regen_newgen_face_bank",
    ),
    "6122faa1-720b-436b-9205-83d0c5d9f1a9": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/North european/Dark Brown/769.png",
        "gtex_regen_newgen_face_bank",
    ),
    "823b33db-2822-4624-bc41-9f4731cc7406": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657818/players/wonderkids/wk_823b33db_asuma_ikari.jpg",
        "transfermarkt",
    ),
    "69871eab-4484-488e-8a63-d6ba2d58b0c3": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657765/players/wonderkids/wk_69871eab_auwal_ibrahim.jpg",
        "transfermarkt",
    ),
    "1cd9c5b8-1fd4-4de1-97df-24fb45fdbf0e": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657629/players/wonderkids/wk_1cd9c5b8_axel_koukaba.jpg",
        "transfermarkt",
    ),
    "84278bd7-bff5-440f-8019-7a1c1b23bdc8": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/North european/Dark Brown/Untitled-122 copy.png",
        "gtex_regen_newgen_face_bank",
    ),
    "83967c16-7fc1-448f-bee6-e48585657169": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/Middle east/Dark Brown/Untitled-240 copy.png",
        "gtex_regen_newgen_face_bank",
    ),
    "fa8b41d6-43af-4c9c-945e-41d04ba6123a": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/African/Dark Brown/africa-darkbrown-100.png",
        "gtex_regen_newgen_face_bank",
    ),
    "555706db-0aef-4188-8536-e0368839ce51": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793656334/players/wonderkids/wk_555706db_baba_moriba_kourouma.png",
        "sofifa_cloudinary",
    ),
    "184ad772-be31-44ca-9a79-77b53756ff7d": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/North european/Dark Brown/973.png",
        "gtex_regen_newgen_face_bank",
    ),
    "3bb3124a-4c4f-4ee1-8af0-6be2cffc3296": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657910/players/wonderkids/wk_3bb3124a_baran__zmen.png",
        "transfermarkt",
    ),
    "686e4611-e251-4dbe-aee0-808e8090647e": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/Hispanic/Dark Brown/427.png",
        "gtex_regen_newgen_face_bank",
    ),
    "dc447e33-f189-4eea-bde4-4090c6b2747c": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793658408/players/wonderkids/wk_dc447e33_believe_munongo.png",
        "migrated_to_cloudinary",
    ),
    "faeed15a-35fe-41d7-908b-04fd8ece9b83": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/South european/Dark Brown/Untitled-18 copy.png",
        "gtex_regen_newgen_face_bank",
    ),
    "985675f4-da97-42c0-acfa-6300a2caec35": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657885/players/wonderkids/wk_985675f4_bendito_mantato.jpg",
        "transfermarkt",
    ),
    "f498e483-5af6-425e-8a92-56ad1f73e450": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/Hispanic/Dark Brown/1232.png",
        "gtex_regen_newgen_face_bank",
    ),
    "5233f9e3-6175-4e03-aff4-4a2dab1aed5c": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/Hispanic/Dark Brown/823.png",
        "gtex_regen_newgen_face_bank",
    ),
    "1cf947e8-c644-454b-97b5-f42eaa244cef": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793659128/players/wonderkids/wk_1cf947e8_benjamin_fredrick.webp",
        "transfermarkt_uploaded",
    ),
    "6e66c48b-be58-4c9a-b40b-71e012afd105": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657626/players/wonderkids/wk_6e66c48b_benjamin_ley.jpg",
        "transfermarkt",
    ),
    "7edead40-f8de-4bfd-933d-a994c98101ee": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793656358/players/wonderkids/wk_7edead40_benjamin_mendy.png",
        "sofifa_cloudinary",
    ),
    "0cc8e889-2d5d-4bd3-88cb-c7235c4c62cd": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657816/players/wonderkids/wk_0cc8e889_beno_t_assou_ekotto.jpg",
        "transfermarkt",
    ),
    "3f9140ed-3dcb-4352-8c28-a44b826070ee": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657840/players/wonderkids/wk_3f9140ed_berat_lus.png",
        "transfermarkt",
    ),
    "a610e071-c66a-4efc-9327-d0177bae8e17": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/North european/Dark Brown/Untitled-60 copy.png",
        "gtex_regen_newgen_face_bank",
    ),
    "760fe051-9c26-406e-a4c2-3e833a50bd84": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/North european/Dark Brown/850.png",
        "gtex_regen_newgen_face_bank",
    ),
    "7c02be2a-559e-4971-a850-05727879ac7a": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657843/players/wonderkids/wk_7c02be2a_boran_elig_zel.jpg",
        "transfermarkt",
    ),
    "842961ba-6dd7-494b-8108-8ce101891c1c": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657676/players/wonderkids/wk_842961ba_boris_mamuzah_lum.jpg",
        "transfermarkt",
    ),
    "80746b0b-c283-4955-adb0-198d2558360c": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/South european/Dark Brown/401.png",
        "gtex_regen_newgen_face_bank",
    ),
    "cb838881-89ed-4d96-b152-9420ca8aecd7": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/South european/Dark Brown/586.png",
        "gtex_regen_newgen_face_bank",
    ),
    "00a6c22a-7d7e-43a5-8871-d035c9d2ac76": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657783/players/wonderkids/wk_00a6c22a_brad_mantsounga.png",
        "transfermarkt",
    ),
    "8fcb1dbc-2ca4-485f-b1a7-87e412f58bc8": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657870/players/wonderkids/wk_8fcb1dbc_braiden_graham.jpg",
        "transfermarkt",
    ),
    "4a67a967-3368-41cf-b1ce-5392a6143af3": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657785/players/wonderkids/wk_4a67a967_brando_bailey_joseph.jpg",
        "transfermarkt",
    ),
    "b3c3f913-b63b-4154-9421-efcc2d8ea3cf": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/North european/Dark Brown/800.png",
        "gtex_regen_newgen_face_bank",
    ),
    "e07469e3-bc9a-4b2c-8a5b-662b8a77c9e9": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/Mixed/Dark Brown/africa-darkbrown-248.png",
        "gtex_regen_newgen_face_bank",
    ),
    "9f954cd8-1842-4463-9f4c-9673379a9c23": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657731/players/wonderkids/wk_9f954cd8_breno_vereza.png",
        "transfermarkt",
    ),
    "bb9b29b2-f4c7-468d-bc3f-b1a9e2090f00": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657856/players/wonderkids/wk_bb9b29b2_bruno_alves.jpg",
        "transfermarkt",
    ),
    "08b3e23e-b290-4a46-bc54-86177753a4f5": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793658397/players/wonderkids/wk_08b3e23e_buba_sangar.png",
        "migrated_to_cloudinary",
    ),
    "46701d65-c2a0-4413-b20a-ced4693398ad": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/South european/Dark Brown/460.png",
        "gtex_regen_newgen_face_bank",
    ),
    "0d403ece-9cd8-4ae2-9f85-3b6a420d03ef": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/Mixed/Dark Brown/africa-darkbrown-73.png",
        "gtex_regen_newgen_face_bank",
    ),
    "bd51fcfc-3ac9-425c-9345-c762966a2648": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657806/players/wonderkids/wk_bd51fcfc_caleb_yirenkyi.jpg",
        "transfermarkt",
    ),
    "5e1b77ee-65c3-422c-8422-f86009c831a9": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657681/players/wonderkids/wk_5e1b77ee_callan_hamill.jpg",
        "transfermarkt",
    ),
    "52bd5bef-03b5-46ce-9978-3f7290a86e72": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/North european/Dark Brown/850.png",
        "gtex_regen_newgen_face_bank",
    ),
    "85607f34-35af-4ce6-a7d2-ca1b25a2aec5": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/Mixed/Dark Brown/africa-darkbrown-16.png",
        "gtex_regen_newgen_face_bank",
    ),
    "eca909f7-4a35-43f8-82b2-f873ca8a9bcb": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657640/players/wonderkids/wk_eca909f7_calvin_diakite.jpg",
        "transfermarkt",
    ),
    "34ec7b5f-8c8a-447a-9cb0-859b799e8672": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/North european/Dark Brown/Untitled-201 copy.png",
        "gtex_regen_newgen_face_bank",
    ),
    "bd2880ae-b04e-41e1-8bb1-3d4d59f4c7f9": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657720/players/wonderkids/wk_bd2880ae_carlos_al_s.jpg",
        "transfermarkt",
    ),
    "63644423-1e80-4d63-a360-1b775f50814c": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793656355/players/wonderkids/wk_63644423_carlos_eduardo.png",
        "sofifa_cloudinary",
    ),
    "9841a79f-ded2-4ccc-8b7c-068e1b75e4f7": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657792/players/wonderkids/wk_9841a79f_cassiano_kiala.jpg",
        "transfermarkt",
    ),
    "98d70d6e-5145-4374-91b7-c6604fb3b957": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657714/players/wonderkids/wk_98d70d6e_cauan_baptistella.png",
        "transfermarkt",
    ),
    "7d36551d-f4ad-4ebf-bcf3-5fb4d4122887": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657706/players/wonderkids/wk_7d36551d_cauan_baptistella.png",
        "transfermarkt",
    ),
    "0f7bdb9d-467a-4a51-a0b1-ee046a63b5ba": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793658396/players/wonderkids/wk_0f7bdb9d_cavan_sullivan.jpg",
        "migrated_to_cloudinary",
    ),
    "d29777ae-4889-4feb-8474-8adce3e5297c": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657829/players/wonderkids/wk_d29777ae_cel_as_ingenthron.jpg",
        "transfermarkt",
    ),
    "aa31114b-3604-4e6a-a892-82009283ae24": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657759/players/wonderkids/wk_aa31114b_cha_n_ghrissi.png",
        "transfermarkt",
    ),
    "5d0d2a21-3083-4f0e-b72c-7229c4675326": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/North european/Dark Brown/1004.png",
        "gtex_regen_newgen_face_bank",
    ),
    "e15bb18a-c4c9-4a57-baf4-3121abd09087": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/North european/Dark Brown/733.png",
        "gtex_regen_newgen_face_bank",
    ),
    "ce48b4e3-0299-4c4a-9328-e7d482747333": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/North european/Dark Brown/523.png",
        "gtex_regen_newgen_face_bank",
    ),
    "ce370c50-7626-440e-a22d-1fdde5d77856": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657773/players/wonderkids/wk_ce370c50_chibuzo_nwoko.jpg",
        "transfermarkt",
    ),
    "d66adc57-4647-430c-8b1d-ffb5a56b60c3": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997857/generated-media/regen_newgen_faces/script_skin_hair/African/Black/africa-black-129.png",
        "gtex_regen_newgen_face_bank",
    ),
    "bee9c708-8cef-4fca-9395-81c2624b0292": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657899/players/wonderkids/wk_bee9c708_chivano_wijks.jpg",
        "transfermarkt",
    ),
    "77084e17-224a-4f81-9582-1e3b39ef94ce": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657909/players/wonderkids/wk_77084e17_chris_afanou.jpg",
        "transfermarkt",
    ),
    "f68e6db2-92da-4feb-acdf-cf920bf63038": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/Mixed/Dark Brown/africa-darkbrown-228.png",
        "gtex_regen_newgen_face_bank",
    ),
    "cc97bc98-f013-4bda-a741-fa2d0982b5eb": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657880/players/wonderkids/wk_cc97bc98_christian_dunbar_mcdonald.jpg",
        "transfermarkt",
    ),
    "6d5b9ffa-ead5-4088-81b5-aa492e723943": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/Mixed/Dark Brown/africa-darkbrown-109.png",
        "gtex_regen_newgen_face_bank",
    ),
    "291628ed-12a3-4415-9705-92e9d4cd7ff9": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/North european/Dark Brown/834.png",
        "gtex_regen_newgen_face_bank",
    ),
    "91c4f651-1aee-464b-93b1-27dcdf010e41": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/South european/Dark Brown/1004.png",
        "gtex_regen_newgen_face_bank",
    ),
    "b816ccd1-ac95-4639-baaa-65050d2a161e": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/South european/Dark Brown/643.png",
        "gtex_regen_newgen_face_bank",
    ),
    "37c386ad-bd73-4e86-b85d-a55c9a55258b": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793656183/players/wonderkids/wk_37c386ad_dani_fern_ndez.png",
        "sofifa_cloudinary",
    ),
    "4e5d69a4-c615-4436-b23f-7e8a65390155": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657715/players/wonderkids/wk_4e5d69a4_dani_mu_oz.jpg",
        "transfermarkt",
    ),
    "d1749cbb-6dcd-4d3c-8091-50a271b64b03": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793658420/players/wonderkids/wk_d1749cbb_daniel_daga.jpg",
        "migrated_to_cloudinary",
    ),
    "14d9be6e-78c6-4b72-9324-4ea274a2c25a": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657817/players/wonderkids/wk_14d9be6e_daniel_job.jpg",
        "transfermarkt",
    ),
    "f375543e-7d36-42d4-8e86-bf9609f10633": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/North european/Dark Brown/811.png",
        "gtex_regen_newgen_face_bank",
    ),
    "cea7c86b-e497-4ba9-9e34-27ac41be2e4d": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657885/players/wonderkids/wk_cea7c86b_dante_headley.jpg",
        "transfermarkt",
    ),
    "1fdfc02d-f7e6-400b-8ca2-2caaa6fcb989": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793658410/players/wonderkids/wk_1fdfc02d_darryl_bakola.png",
        "migrated_to_cloudinary",
    ),
    "35cc14e6-6a50-4f19-9548-a6f764b3bd3f": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793658414/players/wonderkids/wk_35cc14e6_darryl_bakola.png",
        "migrated_to_cloudinary",
    ),
    "053987f7-d7cb-4201-8ac2-c98d6e6513c4": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/North european/Dark Brown/755.png",
        "gtex_regen_newgen_face_bank",
    ),
    "6a07b59d-e664-41b8-9d26-e488ee14d2ae": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/Mixed/Dark Brown/africa-darkbrown-86.png",
        "gtex_regen_newgen_face_bank",
    ),
    "0f5ae390-ba1f-4b2c-b50a-81b005a0fc91": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793656334/players/wonderkids/wk_0f5ae390_david_otorbi.png",
        "sofifa_cloudinary",
    ),
    "151895d6-7916-4b75-8370-1154081c5a8a": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793656195/players/wonderkids/wk_151895d6_david_otorbi.png",
        "sofifa_cloudinary",
    ),
    "d531bf4f-1a12-4463-9053-ecc5ef836b3b": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793658417/players/wonderkids/wk_d531bf4f_davinchi.png",
        "migrated_to_cloudinary",
    ),
    "d280e3ad-53fb-4005-a361-946f6038bf44": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657706/players/wonderkids/wk_d280e3ad_deli_hajdini.jpg",
        "transfermarkt",
    ),
    "3467011e-de52-4c88-9704-04ed6cef75da": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/Mixed/Dark Brown/africa-darkbrown-118.png",
        "gtex_regen_newgen_face_bank",
    ),
    "6cd119af-e1f3-4897-881c-e3d11b43e26a": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/Mixed/Dark Brown/africa-darkbrown-22.png",
        "gtex_regen_newgen_face_bank",
    ),
    "48f119ea-f272-4b3e-b009-f210fb24c478": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657838/players/wonderkids/wk_48f119ea_deniz_eren_d_nmezer.jpg",
        "transfermarkt",
    ),
    "d8215277-628d-4dda-9fbd-bf60945cf4a8": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657779/players/wonderkids/wk_d8215277_denner.jpg",
        "transfermarkt",
    ),
    "2462b22b-3fce-476d-89eb-58fc2e17f976": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657748/players/wonderkids/wk_2462b22b_derek_boakye_osei.jpg",
        "transfermarkt",
    ),
    "184f2a5e-8d4d-4426-bfac-e449f3870f00": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/African/Dark Brown/africa-darkbrown-194.png",
        "gtex_regen_newgen_face_bank",
    ),
    "edb1596f-36db-4d63-aa68-0c317a75e153": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/South european/Dark Brown/343.png",
        "gtex_regen_newgen_face_bank",
    ),
    "03be736b-9409-4588-b409-232b08023567": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/South european/Dark Brown/575.png",
        "gtex_regen_newgen_face_bank",
    ),
    "eec9f833-9023-4fff-a140-1ed44950a5e5": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/Hispanic/Dark Brown/808.png",
        "gtex_regen_newgen_face_bank",
    ),
    "7558816d-cc34-474b-a0f0-a5261c0cd717": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793656194/players/wonderkids/wk_7558816d_diego_le_n.png",
        "sofifa_cloudinary",
    ),
    "6ba1173c-f834-44be-9dfc-53182966eac0": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793656204/players/wonderkids/wk_6ba1173c_diego_le_n.png",
        "sofifa_cloudinary",
    ),
    "b0fc54cc-e9ce-4ad2-9ce1-1330013466af": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657677/players/wonderkids/wk_b0fc54cc_diego_ngambia_dzonga.jpg",
        "transfermarkt",
    ),
    "d8a1797c-6d28-42ac-b085-15adec5ba218": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/North european/Dark Brown/Untitled-112 copy.png",
        "gtex_regen_newgen_face_bank",
    ),
    "379d18c2-cd6d-4717-945d-aafe046a8a17": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/African/Dark Brown/africa-darkbrown-109.png",
        "gtex_regen_newgen_face_bank",
    ),
    "25d0b37b-fb65-484f-9eeb-286bfcd29b4f": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/Hispanic/Dark Brown/1226.png",
        "gtex_regen_newgen_face_bank",
    ),
    "0213dab9-df21-4f7b-a0a5-52835c98324c": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/Hispanic/Dark Brown/874.png",
        "gtex_regen_newgen_face_bank",
    ),
    "f1f4124f-ad5d-4145-9bd0-e9f76910271a": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/Hispanic/Dark Brown/265.png",
        "gtex_regen_newgen_face_bank",
    ),
    "bedf1157-8edb-4bd8-a254-3a1fa7f58304": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657749/players/wonderkids/wk_bedf1157_eba_bekir_is.jpg",
        "transfermarkt",
    ),
    "f1ba61fc-265f-46ec-b1c8-705a294381d0": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657764/players/wonderkids/wk_f1ba61fc_ebenezar_harcourt.jpg",
        "transfermarkt",
    ),
    "ae99c394-82b9-45ca-915a-cd91523304b4": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/Hispanic/Dark Brown/776.png",
        "gtex_regen_newgen_face_bank",
    ),
    "7252829c-d6dc-4efb-9ccb-4133d9349551": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657696/players/wonderkids/wk_7252829c_edu_corlat.jpg",
        "transfermarkt",
    ),
    "49a17d05-6b37-4e4c-af43-15e2235b7962": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/Hispanic/Dark Brown/1001.png",
        "gtex_regen_newgen_face_bank",
    ),
    "f1d975aa-2b64-4ade-9a27-378861389c95": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657640/players/wonderkids/wk_f1d975aa_elias_gr_ger.jpg",
        "transfermarkt",
    ),
    "186b69c3-3402-4371-9524-5dc927d82ffc": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/North european/Dark Brown/831.png",
        "gtex_regen_newgen_face_bank",
    ),
    "d4d5f454-d0db-43a5-888b-962824f9291c": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657638/players/wonderkids/wk_d4d5f454_lis_e_blessing.jpg",
        "transfermarkt",
    ),
    "13af2da0-226e-4981-b566-0dcadd0d3cda": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/South european/Dark Brown/271.png",
        "gtex_regen_newgen_face_bank",
    ),
    "810c150e-48e0-4307-9296-5bc10a50d794": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793658418/players/wonderkids/wk_810c150e_eman_ko_po.png",
        "migrated_to_cloudinary",
    ),
    "9db8bdba-8213-49ac-97e0-81b376dbd342": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657626/players/wonderkids/wk_9db8bdba_emerson_nwaneri.jpg",
        "transfermarkt",
    ),
    "ccbc08c1-34fc-4aa8-a493-48305c3d6cd7": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657803/players/wonderkids/wk_ccbc08c1_emile_witbooi.jpg",
        "transfermarkt",
    ),
    "1f29921b-3e30-45fa-bc8c-855d16e1c79d": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657811/players/wonderkids/wk_1f29921b_emile_witbooi.jpg",
        "transfermarkt",
    ),
    "4aacc79c-19cc-4fd0-8c3d-2e33fd5d326b": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657762/players/wonderkids/wk_4aacc79c_emin_eren_sayar.jpg",
        "transfermarkt",
    ),
    "3060ff63-8a75-4d91-a70f-cd9538183da7": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657839/players/wonderkids/wk_3060ff63_emir_dad_k.jpg",
        "transfermarkt",
    ),
    "2529ab29-b3f0-48c8-9cea-bc74b90e7cf4": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657766/players/wonderkids/wk_2529ab29_emmanuel_chukwu.jpg",
        "transfermarkt",
    ),
    "d095ca6d-1a79-4675-91aa-c2ce88be919f": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657897/players/wonderkids/wk_d095ca6d_emmanuel_mbemba_nlandu.jpg",
        "transfermarkt",
    ),
    "38339067-9b55-45bf-98e9-426d08cdfdb4": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657750/players/wonderkids/wk_38339067_emre__n_var.jpg",
        "transfermarkt",
    ),
    "87085e84-fd6e-4d16-acf4-1a8aed9d4554": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657742/players/wonderkids/wk_87085e84_enric_garcia.jpg",
        "transfermarkt",
    ),
    "4fd82a98-d41f-4447-8717-052acfc5cbf3": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793656212/players/wonderkids/wk_4fd82a98_enrico.png",
        "sofifa_cloudinary",
    ),
    "a3b166a8-f365-4e2e-ae05-8f843a9811c5": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793656209/players/wonderkids/wk_a3b166a8_enrico.png",
        "sofifa_cloudinary",
    ),
    "2cda799f-7097-4690-9e7a-4c15ad7726eb": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/South european/Dark Brown/859.png",
        "gtex_regen_newgen_face_bank",
    ),
    "93b1e044-dc70-4ecb-a942-fb271d992928": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793656206/players/wonderkids/wk_93b1e044_enzo.png",
        "sofifa_cloudinary",
    ),
    "f62ab4a0-4263-4801-bb0f-3851f304f8d1": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657877/players/wonderkids/wk_f62ab4a0_enzo_duarte.jpg",
        "transfermarkt",
    ),
    "eeee12e7-7e0b-4eea-8f69-ba88e9171612": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657877/players/wonderkids/wk_eeee12e7_enzo_molebe.png",
        "transfermarkt",
    ),
    "2148507b-5c7a-4834-9c6b-148974520aec": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/Mixed/Dark Brown/africa-darkbrown-136.png",
        "gtex_regen_newgen_face_bank",
    ),
    "8fed4a1c-ada5-471b-bcf7-f5424556da0a": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/Mixed/Dark Brown/africa-darkbrown-175.png",
        "gtex_regen_newgen_face_bank",
    ),
    "add8c1b4-3dae-4ed6-9a90-25d8c1a29ab1": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657836/players/wonderkids/wk_add8c1b4_enzo_sternal.jpg",
        "transfermarkt",
    ),
    "d552dd64-e515-4707-9c3e-c65428d68eb7": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/South european/Dark Brown/1151.png",
        "gtex_regen_newgen_face_bank",
    ),
    "53900660-7360-415b-a325-6f836abae656": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/Hispanic/Dark Brown/730.png",
        "gtex_regen_newgen_face_bank",
    ),
    "a08f9965-cc28-43d0-9dce-2903993fab37": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/North european/Dark Brown/811.png",
        "gtex_regen_newgen_face_bank",
    ),
    "993f0334-49e0-4ff7-8a09-34adb572ea04": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657628/players/wonderkids/wk_993f0334_exaouse_vunguidica.jpg",
        "transfermarkt",
    ),
    "83b8df79-e6e8-4a2d-b7ca-41c2ecc0b0c0": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/Hispanic/Dark Brown/562.png",
        "gtex_regen_newgen_face_bank",
    ),
    "da2d3215-886e-4b4b-9dc1-09ff43840014": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657650/players/wonderkids/wk_da2d3215_fabrice_muamba.jpg",
        "transfermarkt",
    ),
    "bfbab9c8-0fb2-4eee-8ac8-f6287ddcd7ae": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793656353/players/wonderkids/wk_bfbab9c8_fabricio.png",
        "sofifa_cloudinary",
    ),
    "5e705919-a92f-4669-ac82-224722574ebb": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657730/players/wonderkids/wk_5e705919_facundo_jainikoski.jpg",
        "transfermarkt",
    ),
    "1d0e352e-d94b-4c08-b632-4db0d16ab732": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657841/players/wonderkids/wk_1d0e352e_fadi_zarqelain.jpg",
        "transfermarkt",
    ),
    "c52caac6-2f20-472c-a634-a318b07fc768": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657817/players/wonderkids/wk_c52caac6_faris_tahiru.jpg",
        "transfermarkt",
    ),
    "a85ed4e2-037f-461c-b08f-da7e078c6b4e": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/North european/Dark Brown/628.png",
        "gtex_regen_newgen_face_bank",
    ),
    "bd16a8f4-6250-4ed3-b4d9-e6da2d74129a": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657721/players/wonderkids/wk_bd16a8f4_felipe_esquivel.jpg",
        "transfermarkt",
    ),
    "c1a3a0d1-5c14-4053-a542-821d297c376d": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657832/players/wonderkids/wk_c1a3a0d1_felipe_esquivel.jpg",
        "transfermarkt",
    ),
    "03eca04d-05c2-4f4e-95b3-e0d986165a97": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657866/players/wonderkids/wk_03eca04d_felipe_morais.png",
        "transfermarkt",
    ),
    "9e0f5b46-e695-4453-80a9-d52519ef7834": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/South european/Dark Brown/543.png",
        "gtex_regen_newgen_face_bank",
    ),
    "70b4b57c-028e-43c1-bcc3-2c49d1837a48": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793658420/players/wonderkids/wk_70b4b57c_femi_azeez.png",
        "migrated_to_cloudinary",
    ),
    "15cae40c-bb13-4d0b-9677-6bf67e48a2ae": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793658414/players/wonderkids/wk_15cae40c_fernando_dickes.png",
        "migrated_to_cloudinary",
    ),
    "d53aece5-c2c1-4cae-9790-7e9197a718d3": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/North european/Dark Brown/Untitled-110 copy.png",
        "gtex_regen_newgen_face_bank",
    ),
    "b59166e1-9b1e-4fa4-ab0d-3614f62f0c82": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657660/players/wonderkids/wk_b59166e1_finn_inglethorpe.jpg",
        "transfermarkt",
    ),
    "e860b047-c9e0-4955-828f-a057ce10a669": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657644/players/wonderkids/wk_e860b047_finn_sherlock.jpg",
        "transfermarkt",
    ),
    "ff813d9b-5030-4c86-96a3-641c844b26fa": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657902/players/wonderkids/wk_ff813d9b_florian_hellstern.jpg",
        "transfermarkt",
    ),
    "629bffa1-f915-4db6-94d5-9592be5fc859": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657636/players/wonderkids/wk_629bffa1_floyd_samba.jpg",
        "transfermarkt",
    ),
    "5277a7ae-48ce-4eef-8f77-0fb836e75dc6": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/Hispanic/Dark Brown/986.png",
        "gtex_regen_newgen_face_bank",
    ),
    "087e5296-f61e-4d62-87dd-9824e80c291a": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/South european/Dark Brown/478.png",
        "gtex_regen_newgen_face_bank",
    ),
    "f1cb85b0-5718-4009-8b3d-32e6f646ff1e": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/Hispanic/Dark Brown/1188.png",
        "gtex_regen_newgen_face_bank",
    ),
    "42fc73c5-b49d-4106-9f53-9cf86c96fe7e": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657804/players/wonderkids/wk_42fc73c5_frank_egwuatu.jpg",
        "transfermarkt",
    ),
    "b817f536-6622-402b-b070-61c0bf96ce60": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/North european/Dark Brown/1033.png",
        "gtex_regen_newgen_face_bank",
    ),
    "3b4b6adc-b9f8-4e77-a0c3-df532dafdaa2": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657645/players/wonderkids/wk_3b4b6adc_freddie_lawrie.jpg",
        "transfermarkt",
    ),
    "c96e0bce-d323-4776-b7bb-007d01e9da26": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657887/players/wonderkids/wk_c96e0bce_freddy_bernal.jpg",
        "transfermarkt",
    ),
    "23c9bda4-01b9-4565-a6d4-80372f170fcd": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657735/players/wonderkids/wk_23c9bda4_fynn_schenten.jpg",
        "transfermarkt",
    ),
    "23d9a82a-00a2-46df-aaae-fb63f231f0ff": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/South european/Dark Brown/994.png",
        "gtex_regen_newgen_face_bank",
    ),
    "c4da752a-19a9-41e0-adc3-5e3c6e4cfc9c": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793656335/players/wonderkids/wk_c4da752a_gabriel_rodr_guez.png",
        "sofifa_cloudinary",
    ),
    "e45f6755-603b-4a6f-a793-85815db43f43": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/Mixed/Dark Brown/africa-darkbrown-228.png",
        "gtex_regen_newgen_face_bank",
    ),
    "c5b8c7b9-1438-44a7-90e2-3a4a710ab68a": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657806/players/wonderkids/wk_c5b8c7b9_gaoussou_diarra.jpg",
        "transfermarkt",
    ),
    "f9f208e4-17de-4df2-bcb7-c44678a28ecb": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657895/players/wonderkids/wk_f9f208e4_gazik_ibragimov.png",
        "transfermarkt",
    ),
    "60fa52b3-2b5d-4d39-8d0f-54dace24eb59": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/Mixed/Dark Brown/africa-darkbrown-218.png",
        "gtex_regen_newgen_face_bank",
    ),
    "0151ec8c-be03-49f2-a453-0f71b720d8a3": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657888/players/wonderkids/wk_0151ec8c_george_hemmings.jpg",
        "transfermarkt",
    ),
    "6acfc203-85d6-48a0-bcfe-5946af5d89c7": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/African/Dark Brown/africa-darkbrown-57.png",
        "gtex_regen_newgen_face_bank",
    ),
    "6686d742-6dce-4fca-9eec-9cd50e8641a6": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793656346/players/wonderkids/wk_6686d742_gerald.png",
        "sofifa_cloudinary",
    ),
    "f13e6e19-8186-45a2-9b85-cce9935ea082": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/South european/Dark Brown/667.png",
        "gtex_regen_newgen_face_bank",
    ),
    "3b58609d-0a84-4969-880b-d0b6dc31349f": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/Hispanic/Dark Brown/1000.png",
        "gtex_regen_newgen_face_bank",
    ),
    "b6fb7249-a545-41ae-afb8-ce94a131a5b4": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/North european/Dark Brown/996.png",
        "gtex_regen_newgen_face_bank",
    ),
    "964c4638-23cb-4cbb-b98c-608d3837840b": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657885/players/wonderkids/wk_964c4638_gibson_nana_adu.jpg",
        "transfermarkt",
    ),
    "84b1281e-1805-4e40-b95c-6fd180195598": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657905/players/wonderkids/wk_84b1281e_gibson_nana_adu.jpg",
        "transfermarkt",
    ),
    "2ad77716-5c3a-4d5c-8330-a600b9d5f7e1": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/Hispanic/Dark Brown/Untitled-55 copy.png",
        "gtex_regen_newgen_face_bank",
    ),
    "cfad4f95-f851-4886-8cb6-f3fca31d866d": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/Mixed/Dark Brown/africa-darkbrown-171.png",
        "gtex_regen_newgen_face_bank",
    ),
    "c37dfccb-32d5-4bf1-95b9-81a0429be8fa": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657728/players/wonderkids/wk_c37dfccb_giovanni_cantizano.png",
        "transfermarkt",
    ),
    "ff752ce1-0b14-49e5-9f46-65dad98eab6a": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657674/players/wonderkids/wk_ff752ce1_godwill_kukonki.jpg",
        "transfermarkt",
    ),
    "68ab96c5-30fb-49b7-9c8b-4cd0b32400e0": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/South european/Dark Brown/1096.png",
        "gtex_regen_newgen_face_bank",
    ),
    "b2679c4a-c69f-4ec1-b467-3be6a2790515": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/South european/Dark Brown/941.png",
        "gtex_regen_newgen_face_bank",
    ),
    "38a2f0f2-0387-45af-937f-a9bcee33e4c5": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/Mixed/Dark Brown/africa-darkbrown-75.png",
        "gtex_regen_newgen_face_bank",
    ),
    "b79cc826-28c7-43c4-91a4-7653c03f454f": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793658404/players/wonderkids/wk_b79cc826_guilherme_alves.png",
        "migrated_to_cloudinary",
    ),
    "a87f336a-1f6a-4cec-8bd4-61bfcf0c055b": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/Mixed/Dark Brown/africa-darkbrown-75.png",
        "gtex_regen_newgen_face_bank",
    ),
    "bad2a29a-fbe4-4d8b-88ed-5ec8147cd18e": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793656330/players/wonderkids/wk_bad2a29a_guille_l_pez.png",
        "sofifa_cloudinary",
    ),
    "39991b26-2491-4db0-bb75-3e922bcbec48": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/South european/Dark Brown/1108.png",
        "gtex_regen_newgen_face_bank",
    ),
    "bfbf7bb1-39ce-4dd7-84f5-9ea036786415": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/South european/Dark Brown/1116.png",
        "gtex_regen_newgen_face_bank",
    ),
    "ffbfd417-d9ca-4138-85d9-611c7c12df33": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/North european/Dark Brown/709.png",
        "gtex_regen_newgen_face_bank",
    ),
    "d3d75031-9136-470a-a98e-4d3e13cac3b2": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657784/players/wonderkids/wk_d3d75031_hamza_abdelkarim.jpg",
        "transfermarkt",
    ),
    "730fec17-e122-4f9a-b784-a703b2374d96": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/Mixed/Dark Brown/africa-darkbrown-138.png",
        "gtex_regen_newgen_face_bank",
    ),
    "257150ec-abdf-41af-b185-7d7e1a89e9ab": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657785/players/wonderkids/wk_257150ec_harrison_miles.jpg",
        "transfermarkt",
    ),
    "5823d94a-912a-46ac-b7b9-75ef32d8d7bb": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657656/players/wonderkids/wk_5823d94a_harry_gray.jpg",
        "transfermarkt",
    ),
    "a380717e-468b-41a1-846e-d370bafc6a08": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657669/players/wonderkids/wk_a380717e_harry_howell.jpg",
        "transfermarkt",
    ),
    "5154aca6-1fd3-46ab-9510-1c1c36dc246d": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657672/players/wonderkids/wk_5154aca6_harvey_higgins.jpg",
        "transfermarkt",
    ),
    "fe5fb178-130c-4ec5-9ad8-003cd3934389": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657647/players/wonderkids/wk_fe5fb178_harvey_owen.jpg",
        "transfermarkt",
    ),
    "1aa2b79a-79c6-4070-9b6f-5f29041f633e": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/North european/Dark Brown/837.png",
        "gtex_regen_newgen_face_bank",
    ),
    "fbf594b2-c41a-4065-8116-37a507d8a46a": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657879/players/wonderkids/wk_fbf594b2_heze_grimwade.jpg",
        "transfermarkt",
    ),
    "7d9b7ae3-2b61-4914-b700-b688c49f9a74": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793656341/players/wonderkids/wk_7d9b7ae3_hodei_arrillaga.png",
        "sofifa_cloudinary",
    ),
    "31d5ca9a-d7b2-4067-8be2-b2ab1f0fc382": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657818/players/wonderkids/wk_31d5ca9a_homare_tokuda.jpg",
        "transfermarkt",
    ),
    "89783cd2-1d83-4623-b59a-9e1ebd5e0a35": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/Middle east/Dark Brown/Untitled-55 copy.png",
        "gtex_regen_newgen_face_bank",
    ),
    "9dc00798-cdd1-4c52-a71f-51d8b3eed31f": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657745/players/wonderkids/wk_9dc00798_hugo_barrachina.jpg",
        "transfermarkt",
    ),
    "940bb337-90f2-4e43-90ff-4078ccc483b6": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/South european/Dark Brown/Untitled-85 copy.png",
        "gtex_regen_newgen_face_bank",
    ),
    "35d45e9b-d8be-45e3-9b53-7d739d00db64": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657729/players/wonderkids/wk_35d45e9b_ian_bobadilla.jpg",
        "transfermarkt",
    ),
    "ebe7b56f-7ca2-4b60-9347-71294e709b3c": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657824/players/wonderkids/wk_ebe7b56f_ian_menc_a.jpg",
        "transfermarkt",
    ),
    "0afe4767-a723-4cad-8ac2-6a279fb8464c": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/South european/Dark Brown/1106.png",
        "gtex_regen_newgen_face_bank",
    ),
    "3def94b1-6ed3-4613-84f7-979b7c3d03ce": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657802/players/wonderkids/wk_3def94b1_ibraheem_mahfus_ajasa.png",
        "transfermarkt",
    ),
    "eac28ed7-2f17-40c6-8a4e-8f4fe4796afb": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793658413/players/wonderkids/wk_eac28ed7_ibrahim_mbaye.png",
        "migrated_to_cloudinary",
    ),
    "a334aa80-f177-406b-a737-2dc3168d35e0": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657837/players/wonderkids/wk_a334aa80_ibrahim_rabbaj.png",
        "transfermarkt",
    ),
    "b74f46c5-9938-4934-8df5-668887646ec9": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793656197/players/wonderkids/wk_b74f46c5_ibrahima_sow.png",
        "sofifa_cloudinary",
    ),
    "3ab40e2b-34df-4c22-bbce-39310513fc79": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657903/players/wonderkids/wk_3ab40e2b_idrissa_sabaly.png",
        "transfermarkt",
    ),
    "a55cd0a9-e3ec-4cf3-a646-b956719258a8": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793656330/players/wonderkids/wk_a55cd0a9_ignacio.png",
        "sofifa_cloudinary",
    ),
    "f8cecd2a-bbc0-4bf7-9618-d5aefd6e01d4": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/Hispanic/Dark Brown/576.png",
        "gtex_regen_newgen_face_bank",
    ),
    "ec2c87e7-8d8e-455c-bb20-c1118ba17593": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657741/players/wonderkids/wk_ec2c87e7_igor_oyono.png",
        "transfermarkt",
    ),
    "bd8f6c70-2619-4a62-99e5-ceec4d1c3fd6": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657688/players/wonderkids/wk_bd8f6c70_igor_oyono.png",
        "transfermarkt",
    ),
    "40cc79eb-3697-4869-8a8b-d2d3e77719d4": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657732/players/wonderkids/wk_40cc79eb_igor_tyjon.jpg",
        "transfermarkt",
    ),
    "d70788a0-a589-406d-9837-24b32e0bf3b0": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657705/players/wonderkids/wk_d70788a0_iker_quintero.jpg",
        "transfermarkt",
    ),
    "4bad148b-5a50-4af0-8402-1f1af19b3034": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/South european/Dark Brown/1206.png",
        "gtex_regen_newgen_face_bank",
    ),
    "983ee159-dcb8-4d3d-930f-4dfdf7d8fd95": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793658400/players/wonderkids/wk_983ee159_ilan_jourdren.png",
        "migrated_to_cloudinary",
    ),
    "59ae289a-65e1-47ac-a62a-4b79bc9b5391": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657650/players/wonderkids/wk_59ae289a_ilies_belmokhtar.jpg",
        "transfermarkt",
    ),
    "1035073a-a9ef-4115-8bec-95ebd18cdc6c": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/North european/Dark Brown/1076.png",
        "gtex_regen_newgen_face_bank",
    ),
    "b7844781-d6c5-4626-ad00-a4341edc81cf": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784998219/generated-media/regen_newgen_faces/script_skin_hair/African/Light%20Brown/africa-lightbrown-44.png",
        "gtex_regen_newgen_face_bank",
    ),
    "08af00e0-8c82-464d-85f4-b64d111575d1": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/Hispanic/Dark Brown/Untitled-122 copy.png",
        "gtex_regen_newgen_face_bank",
    ),
    "d1435071-a6ba-4275-abd8-996e4b1cff19": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657706/players/wonderkids/wk_d1435071_ioannis_kechlimparis.jpg",
        "transfermarkt",
    ),
    "d4b4a95a-943f-41a9-a534-154fa7687f3d": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/North european/Dark Brown/294.png",
        "gtex_regen_newgen_face_bank",
    ),
    "4d52ca4d-9271-4490-9a42-777cf1b5bbbc": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/Mixed/Dark Brown/africa-darkbrown-22.png",
        "gtex_regen_newgen_face_bank",
    ),
    "5460dfcc-d752-4603-be43-109cfd888b7a": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657628/players/wonderkids/wk_5460dfcc_isaac_dunn.jpg",
        "transfermarkt",
    ),
    "7c70e56d-aaca-4f90-a55a-48ba73bb5022": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/North european/Dark Brown/Untitled-60 copy.png",
        "gtex_regen_newgen_face_bank",
    ),
    "c3cf6d30-d8a5-416c-999e-d1798bd882e1": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657639/players/wonderkids/wk_c3cf6d30_ishaq_zantour.png",
        "transfermarkt",
    ),
    "bc63a12f-2486-46fb-a987-e72831ac6c6f": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/South european/Dark Brown/992.png",
        "gtex_regen_newgen_face_bank",
    ),
    "00815746-ee00-431a-99cd-690553d45aea": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997909/generated-media/regen_newgen_faces/script_skin_hair/African/Black/africa-black-227.png",
        "gtex_regen_newgen_face_bank",
    ),
    "6625b80d-7f51-4846-a6ea-c6e7c891cb83": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/African/Dark Brown/africa-darkbrown-239.png",
        "gtex_regen_newgen_face_bank",
    ),
    "4c720473-4b7a-4fd3-bf9d-54827c1b5560": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/South european/Dark Brown/962.png",
        "gtex_regen_newgen_face_bank",
    ),
    "fabdb2a1-f9ee-4157-85db-b426c9d99ab2": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793656335/players/wonderkids/wk_fabdb2a1_iv_n_l_pez.png",
        "sofifa_cloudinary",
    ),
    "993e91ec-b6a3-43fa-b283-fe9763e79e85": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657685/players/wonderkids/wk_993e91ec_iv_n_mar.jpg",
        "transfermarkt",
    ),
    "6d2cd63c-620a-4fb0-8e26-68f61f43e583": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657809/players/wonderkids/wk_6d2cd63c_ivan_massek.jpg",
        "transfermarkt",
    ),
    "56e73c55-2e55-4729-942b-b73245250e2a": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657826/players/wonderkids/wk_56e73c55_iv_n_medina.jpg",
        "transfermarkt",
    ),
    "01732eb3-0fc1-4bf4-9452-0fb61d98cc9e": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/South european/Dark Brown/660.png",
        "gtex_regen_newgen_face_bank",
    ),
    "85176542-a78e-4920-94aa-f7aeadbe8a91": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/South european/Dark Brown/713.png",
        "gtex_regen_newgen_face_bank",
    ),
    "d514d17a-f609-489c-abe2-b3957c5fbab3": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657848/players/wonderkids/wk_d514d17a_jack_kortkamp.jpg",
        "transfermarkt",
    ),
    "7ae40a4b-5c29-4546-af47-fa7ee461f24a": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657893/players/wonderkids/wk_7ae40a4b_jack_porter.jpg",
        "transfermarkt",
    ),
    "c36a04a4-287d-48ce-83a1-73181aa23e1f": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/North european/Dark Brown/776.png",
        "gtex_regen_newgen_face_bank",
    ),
    "31bee06d-98c2-46da-98da-09d79f10053b": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/South european/Dark Brown/750.png",
        "gtex_regen_newgen_face_bank",
    ),
    "34f0c434-473b-4d4d-9fb6-669d31685455": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/South european/Dark Brown/621.png",
        "gtex_regen_newgen_face_bank",
    ),
    "13e2e4eb-e872-4d48-b93f-2b4b2851f646": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/South european/Dark Brown/860.png",
        "gtex_regen_newgen_face_bank",
    ),
    "951703f3-5795-4ac9-b96a-e8be3208288f": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/North european/Dark Brown/519.png",
        "gtex_regen_newgen_face_bank",
    ),
    "e1c982b5-7d06-4b4f-b3f7-1bd69a1145a5": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657660/players/wonderkids/wk_e1c982b5_jake_evans.jpg",
        "transfermarkt",
    ),
    "e7cd207d-83dc-442e-a5d1-92629d86e38c": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657707/players/wonderkids/wk_e7cd207d_jamal_kaishvili.png",
        "transfermarkt",
    ),
    "5e914ea1-fc5d-4f75-a974-1dfb1c1e18d1": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/African/Dark Brown/africa-darkbrown-85.png",
        "gtex_regen_newgen_face_bank",
    ),
    "1d1b9662-f4ab-43e4-8eb1-efd777811aaa": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657848/players/wonderkids/wk_1d1b9662_james_overy.png",
        "transfermarkt",
    ),
    "d069868f-fe2d-4c67-963d-3ba41ba83d1d": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/North european/Dark Brown/834.png",
        "gtex_regen_newgen_face_bank",
    ),
    "c57d89d7-2193-4b90-a371-d619575f1d01": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657900/players/wonderkids/wk_c57d89d7_jan_luca_riedl.jpg",
        "transfermarkt",
    ),
    "8a42d47d-cecb-4ae9-bdbb-a9a722bfb26c": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657653/players/wonderkids/wk_8a42d47d_jan_mattis_wehrbein.jpg",
        "transfermarkt",
    ),
    "bd04cbc5-e3dd-4cb9-b63a-8d3fddb63b75": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657750/players/wonderkids/wk_bd04cbc5_jano_monserrate.jpg",
        "transfermarkt",
    ),
    "957a6adc-0042-4696-b1f7-6b6aa76015e8": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/South european/Dark Brown/1031.png",
        "gtex_regen_newgen_face_bank",
    ),
    "d6d54969-c6f1-46e1-aa8d-929e3387fa45": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/South european/Dark Brown/690.png",
        "gtex_regen_newgen_face_bank",
    ),
    "a7a2c9af-08e2-486c-b893-7daa3a57ece8": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/South european/Dark Brown/992.png",
        "gtex_regen_newgen_face_bank",
    ),
    "6417083e-f7cd-475f-805b-5aa066999cca": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/South european/Dark Brown/Untitled-2 copy.png",
        "gtex_regen_newgen_face_bank",
    ),
    "c869d5a1-54a5-4c6d-b841-7fcd425434d2": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/South european/Dark Brown/Untitled-127 copy.png",
        "gtex_regen_newgen_face_bank",
    ),
    "ca17863c-41d9-4494-84a3-ab550520c8c9": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/North european/Dark Brown/1113.png",
        "gtex_regen_newgen_face_bank",
    ),
    "1ec86e62-6c61-49ef-996b-77c4168681db": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657883/players/wonderkids/wk_1ec86e62_jayden_lienou.jpg",
        "transfermarkt",
    ),
    "13fda58c-5e72-46be-bcba-901f0e67c901": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657720/players/wonderkids/wk_13fda58c_jayden_ngwashi.jpg",
        "transfermarkt",
    ),
    "ce304654-9a01-4c2b-a082-e7ea49009378": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793658414/players/wonderkids/wk_ce304654_jean_mambuku.jpg",
        "migrated_to_cloudinary",
    ),
    "f74391e1-0946-489b-97a1-49d21e8d49e7": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657802/players/wonderkids/wk_f74391e1_jeremiah_debrah.jpg",
        "transfermarkt",
    ),
    "e5b3de66-4d0a-4ac9-9c65-d42df0d444f8": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793658403/players/wonderkids/wk_e5b3de66_jeremy_monga.jpg",
        "migrated_to_cloudinary",
    ),
    "97bc9cc6-c22d-4470-aec5-91729a57b947": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793658404/players/wonderkids/wk_97bc9cc6_jeremy_monga.jpg",
        "migrated_to_cloudinary",
    ),
    "e6febbe0-1305-4d5c-ab4c-2c703a11fb55": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657821/players/wonderkids/wk_e6febbe0_jer_nimo_g_mez_mattar.jpg",
        "transfermarkt",
    ),
    "98145153-efac-4fad-898b-3a5786c8082c": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793656325/players/wonderkids/wk_98145153_jessi_da_silva.png",
        "sofifa_cloudinary",
    ),
    "93137c5e-df0f-45d5-b74b-439ceb347dee": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793656336/players/wonderkids/wk_93137c5e_jes_s_rodriguez.png",
        "sofifa_cloudinary",
    ),
    "6946ee29-3908-4ce5-bc38-d8b31dd5688d": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/Mixed/Dark Brown/africa-darkbrown-235.png",
        "gtex_regen_newgen_face_bank",
    ),
    "05ec9f42-f543-4ce9-9b65-7291726702da": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/Mixed/Dark Brown/africa-darkbrown-4.png",
        "gtex_regen_newgen_face_bank",
    ),
    "87da15e9-c0f7-4362-81de-bbf52e84a3f5": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657900/players/wonderkids/wk_87da15e9_jill_stiel.jpg",
        "transfermarkt",
    ),
    "a67561a4-f472-4670-9790-e88199591eaa": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657670/players/wonderkids/wk_a67561a4_jir__pano.jpg",
        "transfermarkt",
    ),
    "9faef701-8c82-45a6-b713-4a392b2feffa": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/North european/Dark Brown/Untitled-18 copy.png",
        "gtex_regen_newgen_face_bank",
    ),
    "bffcbc5d-dfdd-4c9e-91c9-7ac708b39e30": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793656193/players/wonderkids/wk_bffcbc5d_jo_o_victor.png",
        "sofifa_cloudinary",
    ),
    "5c5a71ce-e62c-4da7-8754-7541fe5c677b": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/Hispanic/Dark Brown/1024.png",
        "gtex_regen_newgen_face_bank",
    ),
    "29a0f2b3-990a-4ac3-af11-6cff24d43c6d": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/Hispanic/Dark Brown/850.png",
        "gtex_regen_newgen_face_bank",
    ),
    "0c6ff055-f91d-4a0b-beba-10080c20c9df": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657900/players/wonderkids/wk_0c6ff055_joe_bradshaw.jpg",
        "transfermarkt",
    ),
    "dac25ff8-c922-478b-94f4-203c6f4886ee": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657723/players/wonderkids/wk_dac25ff8_joel_medina.jpg",
        "transfermarkt",
    ),
    "162960a5-da0a-40d7-8528-70f7132036e3": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657791/players/wonderkids/wk_162960a5_jofre_torrents.jpg",
        "transfermarkt",
    ),
    "f9348f63-2e9f-430d-92f1-ef16b73bd746": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657663/players/wonderkids/wk_f9348f63_jona_preu.png",
        "transfermarkt",
    ),
    "2ce33b9d-12fd-4dce-9abb-3b7aa8b5b426": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657634/players/wonderkids/wk_2ce33b9d_jonah_berghoff.jpg",
        "transfermarkt",
    ),
    "631ef18e-1120-4900-8220-664437b48a09": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657710/players/wonderkids/wk_631ef18e_jordi_pesquer.jpg",
        "transfermarkt",
    ),
    "8a08fb53-633d-41b5-bc15-b6292bbb5775": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793656334/players/wonderkids/wk_8a08fb53_jorge.png",
        "sofifa_cloudinary",
    ),
    "74e8d7ba-dcf9-426c-83ab-3d804d2cb1a3": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/South european/Dark Brown/259.png",
        "gtex_regen_newgen_face_bank",
    ),
    "f66ceefa-453e-4f47-8621-038aef624f65": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657652/players/wonderkids/wk_f66ceefa_jorthy_mokio.jpg",
        "transfermarkt",
    ),
    "26d7643c-1655-48fd-b0a9-b9696dae4a93": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657801/players/wonderkids/wk_26d7643c_jos__antonio_reyes.jpg",
        "transfermarkt",
    ),
    "1a96bb1f-86fc-4fbd-9c4b-2ae577b80a83": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657753/players/wonderkids/wk_1a96bb1f_jos__reyes.jpg",
        "transfermarkt",
    ),
    "c9a7d13c-768b-44ee-b9b9-df8722387adf": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793656327/players/wonderkids/wk_c9a7d13c_joseph_wheeler_henry.png",
        "sofifa_cloudinary",
    ),
    "670f897b-f483-4086-b2da-75f7ebfc58c4": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/North european/Dark Brown/517.png",
        "gtex_regen_newgen_face_bank",
    ),
    "35bc4d86-101e-44ff-9c7d-28367967ca45": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/North european/Dark Brown/477.png",
        "gtex_regen_newgen_face_bank",
    ),
    "416ae359-fb85-40a5-8401-2c2766dea1ce": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657793/players/wonderkids/wk_416ae359_josiah_uwakhonye.jpg",
        "transfermarkt",
    ),
    "d096da9e-0353-4338-a903-a45568074f6a": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/South european/Dark Brown/574.png",
        "gtex_regen_newgen_face_bank",
    ),
    "68044d87-9a8c-4636-b251-c8ec273f95a6": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657830/players/wonderkids/wk_68044d87_juan_cruz_meza.png",
        "transfermarkt",
    ),
    "3ebd96c8-4dfc-406f-861b-09544797c155": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657723/players/wonderkids/wk_3ebd96c8_juan_cruz_meza.png",
        "transfermarkt",
    ),
    "484506fc-3331-4053-b981-494080eb6617": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/Hispanic/Dark Brown/1002.png",
        "gtex_regen_newgen_face_bank",
    ),
    "6911d5d5-b2be-4d06-ae1c-78dc64d4d8f2": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/Mixed/Dark Brown/africa-darkbrown-48.png",
        "gtex_regen_newgen_face_bank",
    ),
    "38fe1101-ba65-44d1-a4b4-42bbf0a45f6d": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/South european/Dark Brown/747.png",
        "gtex_regen_newgen_face_bank",
    ),
    "f25f0b14-fcf4-4e75-8c75-2917004a3ddb": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/South european/Dark Brown/Untitled-184 copy.png",
        "gtex_regen_newgen_face_bank",
    ),
    "e2dd4909-7c4e-4e14-a6ce-db7902dbb5b4": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657780/players/wonderkids/wk_e2dd4909_juliano.jpg",
        "transfermarkt",
    ),
    "73627624-5aec-41cf-bcb8-750620f63ea8": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/North european/Dark Brown/Untitled-101 copy.png",
        "gtex_regen_newgen_face_bank",
    ),
    "ea6acc9b-8e0d-450d-9734-a4f7466104a8": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657818/players/wonderkids/wk_ea6acc9b_jumpei_hayakawa.jpg",
        "transfermarkt",
    ),
    "338b64ce-7de3-4f5a-ac34-d50ba857f386": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657640/players/wonderkids/wk_338b64ce_junai_byfield.jpg",
        "transfermarkt",
    ),
    "08d11023-64d6-43a1-a1ad-649f990ff44b": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/Hispanic/Dark Brown/Untitled-131 copy.png",
        "gtex_regen_newgen_face_bank",
    ),
    "58c708fa-36c2-4146-9531-f4cf2db9b29e": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657635/players/wonderkids/wk_58c708fa_kaden_braithwaite.jpg",
        "transfermarkt",
    ),
    "4796e3c7-0e09-4efb-a1b9-287c2e8e6900": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657906/players/wonderkids/wk_4796e3c7_kai_rooney.jpg",
        "transfermarkt",
    ),
    "62be322d-0197-4264-915b-8fbeb29bb468": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793656207/players/wonderkids/wk_62be322d_kaio.png",
        "sofifa_cloudinary",
    ),
    "5d93d583-3ec6-48e7-a2d8-1a3808edd030": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/Mixed/Dark Brown/africa-darkbrown-66.png",
        "gtex_regen_newgen_face_bank",
    ),
    "043398d2-3680-4e16-acfa-b42ed5d2a36f": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/North european/Dark Brown/576.png",
        "gtex_regen_newgen_face_bank",
    ),
    "5c5fc088-53b9-40ce-825e-3ee0a7b98b23": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/North european/Dark Brown/780.png",
        "gtex_regen_newgen_face_bank",
    ),
    "da044e4f-d1f6-4386-a11c-40dbf442d108": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657799/players/wonderkids/wk_da044e4f_kau__prates.jpg",
        "transfermarkt",
    ),
    "d7cdbdc5-9aa4-4262-b645-d1dfd71b7062": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/North european/Dark Brown/450.png",
        "gtex_regen_newgen_face_bank",
    ),
    "98d72ed6-439e-4216-89ea-fa01115ffa0c": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657845/players/wonderkids/wk_98d72ed6_kayke_santos.jpg",
        "transfermarkt",
    ),
    "48d8dae7-04f3-4e2e-ae7b-48539fa32e3a": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657851/players/wonderkids/wk_48d8dae7_kayke_santos.jpg",
        "transfermarkt",
    ),
    "94afc9f6-368b-413c-8ab7-836c2cda70f2": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/North european/Dark Brown/1029.png",
        "gtex_regen_newgen_face_bank",
    ),
    "b6d132ca-35fe-4cb9-9325-1b9c25e6eaaf": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/North european/Dark Brown/Untitled-47 copy.png",
        "gtex_regen_newgen_face_bank",
    ),
    "728938b8-bcd6-478a-920a-536d0185ca89": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657899/players/wonderkids/wk_728938b8_kenan_doganay.jpg",
        "transfermarkt",
    ),
    "734273da-96aa-45fc-aa8e-d31f99fa1258": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/North european/Dark Brown/Untitled-207 copy.png",
        "gtex_regen_newgen_face_bank",
    ),
    "7d8c47c7-ce6a-4841-895a-e25a4dca8ff9": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/East asian/Dark Brown/Untitled-80 copy.png",
        "gtex_regen_newgen_face_bank",
    ),
    "fa04d4a7-afac-49db-a8c2-d579116e91fb": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657891/players/wonderkids/wk_fa04d4a7_khari_ranson.jpg",
        "transfermarkt",
    ),
    "bcd5ae0e-afaa-441c-9d98-0c73a667d5a9": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657793/players/wonderkids/wk_bcd5ae0e_khulumani_ndamane.jpg",
        "transfermarkt",
    ),
    "3179c2d2-f665-4cb3-a804-3adafb6e643f": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657876/players/wonderkids/wk_3179c2d2_kiano_dyer.jpg",
        "transfermarkt",
    ),
    "a5a3938c-6b92-4e50-a788-3dbc9f0be9e5": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/Hispanic/Dark Brown/1045.png",
        "gtex_regen_newgen_face_bank",
    ),
    "60d4bc99-0f5b-419a-b541-6b46b8b66edb": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/North european/Dark Brown/978.png",
        "gtex_regen_newgen_face_bank",
    ),
    "2d2a7af8-f7b5-4bf4-992d-bce209c89e10": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657636/players/wonderkids/wk_2d2a7af8_kobe_barbour.jpg",
        "transfermarkt",
    ),
    "a8c0e47e-71d3-4bbf-88a5-943c7e001d79": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/Middle east/Dark Brown/Untitled-51 copy.png",
        "gtex_regen_newgen_face_bank",
    ),
    "184ad553-fd9f-4d5a-8db0-db2f13c9f55f": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/Middle east/Dark Brown/Untitled-206 copy.png",
        "gtex_regen_newgen_face_bank",
    ),
    "79ddbf64-5f64-41ed-8c64-ae512a067e7c": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793658408/players/wonderkids/wk_79ddbf64_kparobo_arierhi.jpg",
        "migrated_to_cloudinary",
    ),
    "986dfbc4-d5c2-4816-bb02-d24825e64929": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/North european/Dark Brown/955.png",
        "gtex_regen_newgen_face_bank",
    ),
    "24ad42bc-780b-41ab-aa18-627dc3c30630": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/North european/Dark Brown/632.png",
        "gtex_regen_newgen_face_bank",
    ),
    "9b30d810-62b3-47a3-bc6a-df9732bc6162": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793658412/players/wonderkids/wk_9b30d810_kyllian_antonio.png",
        "migrated_to_cloudinary",
    ),
    "90a7f75e-60c3-476e-b859-4f1ba9b410f6": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657888/players/wonderkids/wk_90a7f75e_kyran_thompson.jpg",
        "transfermarkt",
    ),
    "c8acc2bd-0205-4c93-833b-21ebdd44d62f": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657655/players/wonderkids/wk_c8acc2bd_kyrylo_khadasevych.jpg",
        "transfermarkt",
    ),
    "59cbcaf7-07cf-4ad4-a912-4b6dfd52e60d": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657774/players/wonderkids/wk_59cbcaf7_lahlou_akhrib.jpg",
        "transfermarkt",
    ),
    "cfb3e7b9-b8e6-440c-abb6-cf1432dc0fdf": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/f_auto,q_auto/gtex/players/37721324",
        "cloudinary",
    ),
    "1ca638b0-9ec6-41b0-a4e2-37b922f834db": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657859/players/wonderkids/wk_1ca638b0_landry_farr.jpg",
        "transfermarkt",
    ),
    "ea11dddc-e58e-493a-ae09-0b3c853fd765": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/Mixed/Dark Brown/africa-darkbrown-121.png",
        "gtex_regen_newgen_face_bank",
    ),
    "10320da0-4e70-43a9-ae51-871b10b31c43": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/Hispanic/Dark Brown/1047.png",
        "gtex_regen_newgen_face_bank",
    ),
    "1f90a9fa-36fd-4ee2-82a4-d440cf97d938": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657660/players/wonderkids/wk_1f90a9fa_leeron_danioko.jpg",
        "transfermarkt",
    ),
    "b60574c6-770b-45c1-9050-758c3de3b7e8": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/North european/Dark Brown/338.png",
        "gtex_regen_newgen_face_bank",
    ),
    "a19e23e5-f9a1-40d6-bde1-033c16d37939": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/North european/Dark Brown/Untitled-58 copy.png",
        "gtex_regen_newgen_face_bank",
    ),
    "35dab24c-73fb-4e69-9c95-3eb9b84d6534": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657687/players/wonderkids/wk_35dab24c_leo_lemaitre.jpg",
        "transfermarkt",
    ),
    "50e912b3-438c-4801-bc5f-0d358370fbd9": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/North european/Dark Brown/Untitled-76 copy.png",
        "gtex_regen_newgen_face_bank",
    ),
    "18661b0b-4bb8-42f1-8783-0ff88dcc97a2": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657773/players/wonderkids/wk_18661b0b_leonard_ngenge.jpg",
        "transfermarkt",
    ),
    "b7b4a7c5-0c33-4728-afe6-2ec432809ab3": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657869/players/wonderkids/wk_b7b4a7c5_leonard_prescott.jpg",
        "transfermarkt",
    ),
    "3aff6719-d005-4f3a-ad21-047cf23f8acb": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/Hispanic/Dark Brown/1034.png",
        "gtex_regen_newgen_face_bank",
    ),
    "8b6ee8e4-a972-4f6f-ba29-4d117f8f70c5": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/North european/Dark Brown/568.png",
        "gtex_regen_newgen_face_bank",
    ),
    "9f209487-c339-48eb-8830-73f4480bb3e2": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657850/players/wonderkids/wk_9f209487_lewi_richards.jpg",
        "transfermarkt",
    ),
    "2692d934-eb6b-4af7-aab3-8ad8f40b3d60": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/Hispanic/Dark Brown/1042.png",
        "gtex_regen_newgen_face_bank",
    ),
    "ec97ae9b-79ae-4d6d-84e5-7160e948b45a": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657695/players/wonderkids/wk_ec97ae9b_ljubo_puljic.jpg",
        "transfermarkt",
    ),
    "4dd3dacf-a8aa-4c4a-8a5e-dc3c858ddd54": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/North european/Dark Brown/480.png",
        "gtex_regen_newgen_face_bank",
    ),
    "9da3a51b-9be5-4de0-beca-674b460a3d5d": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/North european/Dark Brown/1063.png",
        "gtex_regen_newgen_face_bank",
    ),
    "f3107fa9-b160-4947-84aa-d3db0b575bb4": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/South european/Dark Brown/613.png",
        "gtex_regen_newgen_face_bank",
    ),
    "c54e0e9a-72d0-4d20-aa98-bda378017874": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657853/players/wonderkids/wk_c54e0e9a_louie_bradbury.jpg",
        "transfermarkt",
    ),
    "3496d2d0-72d9-4480-b8d3-13c69f5a4fc5": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/North european/Dark Brown/884.png",
        "gtex_regen_newgen_face_bank",
    ),
    "b9ac06a8-6d85-4e00-a9bc-32b62924ba63": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657658/players/wonderkids/wk_b9ac06a8_louis_page.jpg",
        "transfermarkt",
    ),
    "082c7b06-89d7-4b82-8180-258976d3e9ca": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657714/players/wonderkids/wk_082c7b06_louis_zecevic_john.jpg",
        "transfermarkt",
    ),
    "f63a692f-20e8-4ed6-bac3-058db5841e66": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/North european/Dark Brown/672.png",
        "gtex_regen_newgen_face_bank",
    ),
    "8ec47fce-97f6-411f-aac0-42b4c1b00495": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657908/players/wonderkids/wk_8ec47fce_luca_babl.jpg",
        "transfermarkt",
    ),
    "792828bc-9ff9-43fa-a5f9-953027d88456": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657631/players/wonderkids/wk_792828bc_luca_hampel.jpg",
        "transfermarkt",
    ),
    "6c6a9e4e-ea1f-4a6a-a6d4-9d1d15b65be8": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793658414/players/wonderkids/wk_6c6a9e4e_luca_reggiani.png",
        "migrated_to_cloudinary",
    ),
    "07f456aa-9e54-4d5d-9f3e-81e77ccb4665": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657760/players/wonderkids/wk_07f456aa_luc__williams_barnett.jpg",
        "transfermarkt",
    ),
    "c97d877e-16bd-4f50-9880-17c3e33856d0": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793656356/players/wonderkids/wk_c97d877e_lucas_gabriel.png",
        "sofifa_cloudinary",
    ),
    "61d98200-03d0-423d-b125-fdebc216fd5e": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793656355/players/wonderkids/wk_61d98200_luis_eduardo.png",
        "sofifa_cloudinary",
    ),
    "b6613fa2-4b28-4e6b-9085-ad44b8031bcc": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793656215/players/wonderkids/wk_b6613fa2_luis_felipe.png",
        "sofifa_cloudinary",
    ),
    "92ec7308-5872-46fb-8e97-b9e19bb398af": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/Mixed/Dark Brown/africa-darkbrown-71.png",
        "gtex_regen_newgen_face_bank",
    ),
    "55a04515-2daa-4e66-9653-2ff1c093ffd7": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657849/players/wonderkids/wk_55a04515_luis_ot_vio.jpg",
        "transfermarkt",
    ),
    "29b5da6d-b282-45f6-a81a-302333730c20": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657693/players/wonderkids/wk_29b5da6d_luka_petrovic.jpg",
        "transfermarkt",
    ),
    "2541a98d-f357-4251-a254-ab1d88f318c8": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/South european/Dark Brown/738.png",
        "gtex_regen_newgen_face_bank",
    ),
    "83bddade-2cfd-471a-a561-815d9e167f07": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657643/players/wonderkids/wk_83bddade_mahdi_nicoll_jazuli.jpg",
        "transfermarkt",
    ),
    "666f895a-7951-4679-91e4-749b379224ef": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657672/players/wonderkids/wk_666f895a_makar_kotovshchikov.png",
        "transfermarkt",
    ),
    "eb77aece-e47a-4ef8-8091-f9bc36c8657b": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657661/players/wonderkids/wk_eb77aece_malachi_hardy.jpg",
        "transfermarkt",
    ),
    "14aa42c1-329d-488d-b1b9-ac08623523b0": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793658401/players/wonderkids/wk_14aa42c1_malick_yalcouy.jpg",
        "migrated_to_cloudinary",
    ),
    "528eae9b-e8e8-4778-9af0-e6d588057f21": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657812/players/wonderkids/wk_528eae9b_malik_odeyinka.png",
        "transfermarkt",
    ),
    "860ea9d4-6811-4609-9a60-c92925f65801": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793656330/players/wonderkids/wk_860ea9d4_manu_gonz_lez.png",
        "sofifa_cloudinary",
    ),
    "f1fe2b0c-d070-48a7-8aa2-5acc362d2c97": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/Mixed/Dark Brown/africa-darkbrown-138.png",
        "gtex_regen_newgen_face_bank",
    ),
    "377431f7-27c8-411a-a66c-f7bf545eed61": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/Hispanic/Dark Brown/34545454.png",
        "gtex_regen_newgen_face_bank",
    ),
    "55b83012-11ea-48c5-8daa-fcc0b5731530": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793656335/players/wonderkids/wk_55b83012_marc_dom_nech.png",
        "sofifa_cloudinary",
    ),
    "b3d887da-bc16-4564-8507-fdd17c26dc1c": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793656329/players/wonderkids/wk_b3d887da_marcelino.png",
        "sofifa_cloudinary",
    ),
    "832e6072-52f9-4cff-b215-109a8ca4f31b": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657679/players/wonderkids/wk_832e6072_marcello_trippel.jpg",
        "transfermarkt",
    ),
    "9e36624d-91a2-4f5f-8d89-f258e45902c3": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793656329/players/wonderkids/wk_9e36624d_marco_de_las_s_as.png",
        "sofifa_cloudinary",
    ),
    "d8e523ce-f9f7-47c6-a68f-979632109afd": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793656329/players/wonderkids/wk_d8e523ce_marcos_go_i.png",
        "sofifa_cloudinary",
    ),
    "5b08f2de-b25b-4006-b1ee-65f079df9121": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657703/players/wonderkids/wk_5b08f2de_mario_d_az.jpg",
        "transfermarkt",
    ),
    "1fd55a1b-7414-4af9-839f-5354b03d3261": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657884/players/wonderkids/wk_1fd55a1b_m_rk__m_ndity.jpg",
        "transfermarkt",
    ),
    "82c24f1f-d586-45af-999d-0149c61d2e46": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657629/players/wonderkids/wk_82c24f1f_marli_salmon.jpg",
        "transfermarkt",
    ),
    "168c0e12-3698-466d-9c3e-651c6091573b": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657786/players/wonderkids/wk_168c0e12_martin_j_rgensen.jpg",
        "transfermarkt",
    ),
    "57ca9a26-0dd8-4907-b7cc-9c2afe67c413": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/North european/Dark Brown/561.png",
        "gtex_regen_newgen_face_bank",
    ),
    "bb80e00b-41fe-4045-a958-45a7b0c7db0c": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/Hispanic/Dark Brown/615.png",
        "gtex_regen_newgen_face_bank",
    ),
    "f110ea66-c933-48b8-a21b-903a0baf59f1": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/North european/Dark Brown/Untitled-107 copy.png",
        "gtex_regen_newgen_face_bank",
    ),
    "7ee96bd8-689e-4ed7-b38a-51ea697c9857": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657813/players/wonderkids/wk_7ee96bd8_mathieu_nguefack.jpg",
        "transfermarkt",
    ),
    "95bf8c3e-07c0-4ef8-a587-e12da0d9eb4a": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657734/players/wonderkids/wk_95bf8c3e_mathis_albert.jpg",
        "transfermarkt",
    ),
    "76c45075-0574-439e-b54a-9f8df6863f84": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657659/players/wonderkids/wk_76c45075_mathis_eboue.jpg",
        "transfermarkt",
    ),
    "99978ed3-f025-4b64-b0aa-1d769f74df41": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657657/players/wonderkids/wk_99978ed3_mathis_jangeal.jpg",
        "transfermarkt",
    ),
    "de6de590-780c-425c-becb-648b3d810e15": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/Mixed/Dark Brown/africa-darkbrown-34.png",
        "gtex_regen_newgen_face_bank",
    ),
    "fe3a41a9-0b2f-4fd9-8fcb-4c497ae04111": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/North european/Dark Brown/1032.png",
        "gtex_regen_newgen_face_bank",
    ),
    "0bf2e880-890c-4db5-b9cf-71ffd4c6300e": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657833/players/wonderkids/wk_0bf2e880_mat_as_acevedo.jpg",
        "transfermarkt",
    ),
    "1ab0546c-8afb-4f8c-b36a-766b0ae6d540": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657824/players/wonderkids/wk_1ab0546c_mat_as_acevedo.jpg",
        "transfermarkt",
    ),
    "89596a34-1a42-40ac-bdfa-2c2ffad49262": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/Hispanic/Dark Brown/1030.png",
        "gtex_regen_newgen_face_bank",
    ),
    "5c2b4965-5423-44f9-9522-e61dab539537": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657792/players/wonderkids/wk_5c2b4965_mat_as_satas.jpg",
        "transfermarkt",
    ),
    "87ef20b3-bd08-44ec-99d5-77149683d88e": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657889/players/wonderkids/wk_87ef20b3_matteo_palma.jpg",
        "transfermarkt",
    ),
    "a8154d1c-7b21-4808-b076-698e87962737": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657850/players/wonderkids/wk_a8154d1c_max_hudson.jpg",
        "transfermarkt",
    ),
    "9d8465b6-2049-4bdc-adcb-d94e87b15f74": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/North european/Dark Brown/591.png",
        "gtex_regen_newgen_face_bank",
    ),
    "bfc2dc4c-47db-4b6f-a5e9-11a1010122f2": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657734/players/wonderkids/wk_bfc2dc4c_max_edgar_chabot.jpg",
        "transfermarkt",
    ),
    "986689a9-6872-4a82-8c0c-1fd90f65cd43": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657754/players/wonderkids/wk_986689a9_maximilian_hennig.jpg",
        "transfermarkt",
    ),
    "66093bf9-0fa3-445b-9c8b-449d84bd41eb": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/Middle east/Dark Brown/Untitled-190 copy.png",
        "gtex_regen_newgen_face_bank",
    ),
    "df7c641c-57d5-42bf-8335-f7823066556a": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657812/players/wonderkids/wk_df7c641c_mfundo_vilakazi.jpg",
        "transfermarkt",
    ),
    "e0aea3c2-6de6-4b18-a6ef-0082e472945e": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/African/Dark Brown/africa-darkbrown-44.png",
        "gtex_regen_newgen_face_bank",
    ),
    "1e8dcee2-e45b-4392-9b21-a06cb1f737ed": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657879/players/wonderkids/wk_1e8dcee2_michael_mills.jpg",
        "transfermarkt",
    ),
    "d2bcbd62-4dbf-4296-8428-e289dd16cb92": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657870/players/wonderkids/wk_d2bcbd62_michel_ekodi.png",
        "transfermarkt",
    ),
    "78a40c65-20e8-4048-b9b9-b0c3c8143c97": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793658402/players/wonderkids/wk_78a40c65_mick_schmetgens.png",
        "migrated_to_cloudinary",
    ),
    "160d5ffa-7aec-4aeb-846a-896fbf9622b7": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/South european/Dark Brown/Untitled-23 copy.png",
        "gtex_regen_newgen_face_bank",
    ),
    "fbb773b8-b64c-416d-b80c-ae641d8071ae": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/Mixed/Dark Brown/africa-darkbrown-49.png",
        "gtex_regen_newgen_face_bank",
    ),
    "8b0789f7-ac6b-4d55-b759-3eb82baa4e2e": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657654/players/wonderkids/wk_8b0789f7_miracle_adewole.jpg",
        "transfermarkt",
    ),
    "d46dc2bc-af7c-4846-9adc-47b08658e734": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/North european/Dark Brown/449.png",
        "gtex_regen_newgen_face_bank",
    ),
    "eab25a64-2751-4d70-9e55-82b332a2ced5": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657778/players/wonderkids/wk_eab25a64_mohamed_el_amine_ramdaoui.png",
        "transfermarkt",
    ),
    "b68428c4-17fe-41ef-96fd-2a630f92c025": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/Middle east/Dark Brown/Untitled-56 copy.png",
        "gtex_regen_newgen_face_bank",
    ),
    "4fff8a30-ce8c-48e1-b3b5-3e0b72c5700b": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793656224/players/wonderkids/wk_4fff8a30_mohamed_kader_me_t.png",
        "sofifa_cloudinary",
    ),
    "2aa4cc30-674b-4ae5-bdd0-b47d9ea98367": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657676/players/wonderkids/wk_2aa4cc30_mussa_kaba.jpg",
        "transfermarkt",
    ),
    "152c7997-aa31-4673-bd0e-3f36617bd66a": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/North european/Dark Brown/992.png",
        "gtex_regen_newgen_face_bank",
    ),
    "3567b2da-1508-4f6b-8554-72645660b54a": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/Hispanic/Dark Brown/1098.png",
        "gtex_regen_newgen_face_bank",
    ),
    "5b8ec00d-fd0c-4b4e-9012-b3bf6d6ecc07": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657854/players/wonderkids/wk_5b8ec00d_nadson.png",
        "transfermarkt",
    ),
    "e7446ea5-7ab4-4212-ae74-198e9c33b2bd": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/North european/Dark Brown/295.png",
        "gtex_regen_newgen_face_bank",
    ),
    "fa940d7b-bac4-4ca8-b241-f25ebac7745b": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997922/generated-media/regen_newgen_faces/script_skin_hair/African/Black/africa-black-29.png",
        "gtex_regen_newgen_face_bank",
    ),
    "226f5a02-49b8-45cd-84ff-c2e13703fcc7": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657842/players/wonderkids/wk_226f5a02_nassim_el_massoudi.png",
        "transfermarkt",
    ),
    "0c64bc04-bf2e-473a-a4cb-db1caa58ec3e": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657647/players/wonderkids/wk_0c64bc04_nathan_de_cat.jpg",
        "transfermarkt",
    ),
    "0deff70a-b0cf-4226-b754-e718231eaa44": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/North european/Dark Brown/492.png",
        "gtex_regen_newgen_face_bank",
    ),
    "f9c9a0a9-be8e-4a55-86a3-72ce6651decc": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/North european/Dark Brown/281.png",
        "gtex_regen_newgen_face_bank",
    ),
    "0f3b69c0-b7d2-43c6-beed-b56f69142de9": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657720/players/wonderkids/wk_0f3b69c0_necer_marouane_benzid.jpg",
        "transfermarkt",
    ),
    "567d4e61-8d2a-41d2-925d-e1a01fd6d8f9": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/North european/Dark Brown/424.png",
        "gtex_regen_newgen_face_bank",
    ),
    "fece132f-879c-47c2-8808-81d71922278b": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657868/players/wonderkids/wk_fece132f_neil_pierre.jpg",
        "transfermarkt",
    ),
    "5c8b4f79-f8cf-4c9b-91ad-cb0147b83535": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657791/players/wonderkids/wk_5c8b4f79_nico_anand.jpg",
        "transfermarkt",
    ),
    "24c96ad5-e8e1-4d4d-96c0-503b6bf25030": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/Hispanic/Dark Brown/517.png",
        "gtex_regen_newgen_face_bank",
    ),
    "902c65c6-9685-487f-b909-887acd993123": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/Hispanic/Dark Brown/Untitled-68 copy.png",
        "gtex_regen_newgen_face_bank",
    ),
    "8af33ff9-1ba2-48fd-8d40-c646fa4df05f": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657849/players/wonderkids/wk_8af33ff9_nicolas_bosshardt.jpg",
        "transfermarkt",
    ),
    "4ed9c895-4e2d-4d00-bdf6-1cfe17fa9159": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/Mixed/Dark Brown/africa-darkbrown-48.png",
        "gtex_regen_newgen_face_bank",
    ),
    "33bb410b-36a1-447e-a7e0-a4e415c24df2": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793658406/players/wonderkids/wk_33bb410b_nidal_celik.png",
        "migrated_to_cloudinary",
    ),
    "122c9d84-fb18-430d-9739-e3d1c0148aae": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793658407/players/wonderkids/wk_122c9d84_nidal_celik.png",
        "migrated_to_cloudinary",
    ),
    "fbf473e8-b952-4028-b49c-85add4aac770": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657669/players/wonderkids/wk_fbf473e8_niklas_hildebrandt.jpg",
        "transfermarkt",
    ),
    "5bf09a06-54ac-443f-b75a-c6423292d4e3": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657715/players/wonderkids/wk_5bf09a06_niko_horvat.jpg",
        "transfermarkt",
    ),
    "5260c853-cdd6-4e51-9026-2319b39abb7f": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657886/players/wonderkids/wk_5260c853_niko_horvat.jpg",
        "transfermarkt",
    ),
    "e29ee0b5-b6cc-4004-9a4d-3490ac92ba06": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/North european/Dark Brown/576.png",
        "gtex_regen_newgen_face_bank",
    ),
    "0751eab9-6622-4ae2-b463-e2d9f2539654": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/South european/Dark Brown/489.png",
        "gtex_regen_newgen_face_bank",
    ),
    "98766089-0299-45c3-9328-4de48157ed75": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657898/players/wonderkids/wk_98766089_noah_codjo_evora.jpg",
        "transfermarkt",
    ),
    "8efc6c04-37b6-4532-8cbb-14feb1e3cd8b": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793658414/players/wonderkids/wk_8efc6c04_noah_darvich.png",
        "migrated_to_cloudinary",
    ),
    "b2854467-25ee-4c7b-ad5e-a2e3edcd4aa2": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/North european/Dark Brown/874.png",
        "gtex_regen_newgen_face_bank",
    ),
    "b4153093-5a7e-4503-8fe9-06e198b554fd": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657683/players/wonderkids/wk_b4153093_nunzio_engwanda.jpg",
        "transfermarkt",
    ),
    "75b5992f-775e-49d2-8052-2850eaffbf99": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793658397/players/wonderkids/wk_75b5992f_octavio_ont_vero.jpg",
        "migrated_to_cloudinary",
    ),
    "027f25eb-da14-451c-9a89-01d34a2b0167": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/North european/Dark Brown/1039.png",
        "gtex_regen_newgen_face_bank",
    ),
    "17092737-6fa0-46ea-804c-f9af36551ec8": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/Mixed/Dark Brown/africa-darkbrown-34.png",
        "gtex_regen_newgen_face_bank",
    ),
    "40ac88b8-4bf1-4ff6-9adb-1316234e2b5b": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/North european/Dark Brown/527.png",
        "gtex_regen_newgen_face_bank",
    ),
    "5e8af591-3f33-4e92-97e8-35aee753af3c": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657670/players/wonderkids/wk_5e8af591_ollie_harrison.jpg",
        "transfermarkt",
    ),
    "5b832d79-bb84-4faa-ae28-e5b03162af98": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657764/players/wonderkids/wk_5b832d79_onuralp__akiroglu.png",
        "transfermarkt",
    ),
    "5d5bd64d-b142-4dd3-b056-c86a55c16157": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/South european/Dark Brown/1162.png",
        "gtex_regen_newgen_face_bank",
    ),
    "5d717549-6f86-475e-9533-8f4571e2eb1e": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657699/players/wonderkids/wk_5d717549_scar_gistau.jpg",
        "transfermarkt",
    ),
    "10921e64-7d61-4ff9-bbb3-63ab2b4715da": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657757/players/wonderkids/wk_10921e64_scar_gistau.jpg",
        "transfermarkt",
    ),
    "20c3a107-b3d1-4773-b57c-98020f424337": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793656330/players/wonderkids/wk_20c3a107_owen.png",
        "sofifa_cloudinary",
    ),
    "a476ac3c-3608-483d-889a-c8831ed4c6c0": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/Mixed/Dark Brown/africa-darkbrown-212.png",
        "gtex_regen_newgen_face_bank",
    ),
    "e0244cd4-19fe-4c08-abae-517cb21fd4a5": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657690/players/wonderkids/wk_e0244cd4_pablo_herrera.jpg",
        "transfermarkt",
    ),
    "8c18880b-29f0-477a-9ddc-36cb823695ed": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/Mixed/Dark Brown/africa-darkbrown-48.png",
        "gtex_regen_newgen_face_bank",
    ),
    "389b87ee-e132-4bb3-a2ee-1938f95e2bd4": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/South european/Dark Brown/312.png",
        "gtex_regen_newgen_face_bank",
    ),
    "eb277780-2489-4444-bea3-81d2f6d0117a": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793658397/players/wonderkids/wk_eb277780_paco_cort_s.webp",
        "migrated_to_cloudinary",
    ),
    "cbdc8711-2a3b-4d42-9328-ddb9e4a533b2": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793656333/players/wonderkids/wk_cbdc8711_pau_cabanes.png",
        "sofifa_cloudinary",
    ),
    "f1f7b587-3504-40f7-bf1a-73b90c7d28c9": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793658396/players/wonderkids/wk_f1f7b587_pau_navarro.png",
        "migrated_to_cloudinary",
    ),
    "d7e79dae-93c2-40d0-a144-2515710853a3": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/South european/Dark Brown/314.png",
        "gtex_regen_newgen_face_bank",
    ),
    "fc8e23c4-fbd8-4ca5-a60c-93b1d67103d4": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/North european/Dark Brown/981.png",
        "gtex_regen_newgen_face_bank",
    ),
    "928250fa-263c-4b1a-ac20-a6aa599048cb": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657905/players/wonderkids/wk_928250fa_paul_wienholt.jpg",
        "transfermarkt",
    ),
    "1556b6b2-4028-41bd-a249-1224f4c8fe40": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793656201/players/wonderkids/wk_1556b6b2_pedro_gonz_lez.png",
        "sofifa_cloudinary",
    ),
    "928570f2-8a8a-4759-b7d3-32d614488fe2": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793656202/players/wonderkids/wk_928570f2_pedro_gonz_lez.png",
        "sofifa_cloudinary",
    ),
    "2d9cdcfe-624b-4a51-84cf-3630cd289451": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/Mixed/Dark Brown/africa-darkbrown-92.png",
        "gtex_regen_newgen_face_bank",
    ),
    "6d135d18-f0e0-49cd-b4d1-665e3c5111ef": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657772/players/wonderkids/wk_6d135d18_peter_edokpolor.jpg",
        "transfermarkt",
    ),
    "31b84034-c004-4ae2-a31b-30051f700998": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/North european/Dark Brown/358.png",
        "gtex_regen_newgen_face_bank",
    ),
    "a23c4f7b-2085-494d-b35e-3327230d86bb": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657779/players/wonderkids/wk_a23c4f7b_philipp_maybach.jpg",
        "transfermarkt",
    ),
    "f772c491-6396-4460-af14-c9e51493bb25": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/African/Dark Brown/africa-darkbrown-28.png",
        "gtex_regen_newgen_face_bank",
    ),
    "aa14dbc7-0245-4729-8f87-2a52015f4c09": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/South european/Dark Brown/571.png",
        "gtex_regen_newgen_face_bank",
    ),
    "f9f47d62-52ce-4ff9-ba2f-e54fbfa49c2e": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657766/players/wonderkids/wk_f9f47d62_precious_benjamin.jpg",
        "transfermarkt",
    ),
    "d6ae9e0e-1412-4927-a9d9-28ea5e08fec3": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/Mixed/Dark Brown/africa-darkbrown-134.png",
        "gtex_regen_newgen_face_bank",
    ),
    "265d177a-f214-4b81-8ec6-f4f98303f720": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657641/players/wonderkids/wk_265d177a_rafe_mccormack.jpg",
        "transfermarkt",
    ),
    "11e180ac-e7c0-4e87-a045-f14d24161845": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657735/players/wonderkids/wk_11e180ac_raphael_pavlic.jpg",
        "transfermarkt",
    ),
    "f960b7db-1bf5-4b3b-baff-9fa03dfb63bd": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/North european/Dark Brown/492.png",
        "gtex_regen_newgen_face_bank",
    ),
    "e0f34caf-c151-4a7e-b14c-91b76366b8ea": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793656335/players/wonderkids/wk_e0f34caf_ra_l_exp_sito_martinez.png",
        "sofifa_cloudinary",
    ),
    "89b01bd3-5f0c-4359-aada-f2f5bde16e10": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657707/players/wonderkids/wk_89b01bd3_raul_kumar.jpg",
        "transfermarkt",
    ),
    "159421fc-dbbd-44bf-ac46-c5d094205e42": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657695/players/wonderkids/wk_159421fc_raul_pertea.png",
        "transfermarkt",
    ),
    "4fa3e473-5efd-4361-b1f9-7cf9eba91fed": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657717/players/wonderkids/wk_4fa3e473_rayane_belaid.jpg",
        "transfermarkt",
    ),
    "8396802f-e2a4-4638-9584-08d6c5b2cba7": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657894/players/wonderkids/wk_8396802f_rayane_gbadamassi.jpg",
        "transfermarkt",
    ),
    "14fab584-e1fe-41d0-8479-64b671b0c15f": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657775/players/wonderkids/wk_14fab584_redouane_berkane.jpg",
        "transfermarkt",
    ),
    "db5b205d-28a4-406e-b355-8ee45eb06eda": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657645/players/wonderkids/wk_db5b205d_reggie_walsh.jpg",
        "transfermarkt",
    ),
    "45e0dcfc-c6ab-436c-b8b3-b07ecc142d73": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657629/players/wonderkids/wk_45e0dcfc_reigan_heskey.jpg",
        "transfermarkt",
    ),
    "39d221a0-2d15-4328-8c4d-d0374fe8ee27": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657875/players/wonderkids/wk_39d221a0_r_mi_himbert.jpg",
        "transfermarkt",
    ),
    "440fa7e9-f002-4234-bf8b-521952384cd8": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657811/players/wonderkids/wk_440fa7e9_richard_ajayi.jpg",
        "transfermarkt",
    ),
    "f11f9632-2421-47f0-9fe7-3f91fbd386dc": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/South european/Dark Brown/500.png",
        "gtex_regen_newgen_face_bank",
    ),
    "a82f7d57-dde6-4a0a-b29c-c2fd07217e0d": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/North european/Dark Brown/Untitled-79 copy.png",
        "gtex_regen_newgen_face_bank",
    ),
    "4012b58d-9145-4368-9f4b-0d296f1c7c89": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/Mixed/Dark Brown/africa-darkbrown-99.png",
        "gtex_regen_newgen_face_bank",
    ),
    "9310959b-8411-4ac4-98d7-1c693ceea2ce": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793658419/players/wonderkids/wk_9310959b_robert_turdean.png",
        "migrated_to_cloudinary",
    ),
    "f8ee92ce-a1ee-486b-aa17-266c1d07c554": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657699/players/wonderkids/wk_f8ee92ce_roberto_scaglione.jpg",
        "transfermarkt",
    ),
    "f0eb6220-d18c-4e70-9dfd-be5923eed22e": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/South european/Dark Brown/Untitled-174 copy.png",
        "gtex_regen_newgen_face_bank",
    ),
    "f6066c72-c088-4ae9-bb0b-e63e7496220c": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/Mixed/Dark Brown/africa-darkbrown-171.png",
        "gtex_regen_newgen_face_bank",
    ),
    "4506f43e-7b78-467a-a602-42e47b93a438": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/Hispanic/Dark Brown/1040.png",
        "gtex_regen_newgen_face_bank",
    ),
    "da06a430-6db3-47bb-9b54-a33d0b116e0b": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793656211/players/wonderkids/wk_da06a430_roger.png",
        "sofifa_cloudinary",
    ),
    "9515513a-428b-4e74-b575-fef1fe61ce12": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/North european/Dark Brown/376.png",
        "gtex_regen_newgen_face_bank",
    ),
    "95436fee-5d66-4eb1-8684-5348a256c7d5": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/North european/Dark Brown/1092.png",
        "gtex_regen_newgen_face_bank",
    ),
    "7e3e2252-e2f9-46f1-bab2-a8f62cae5727": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657874/players/wonderkids/wk_7e3e2252_rory_finneran.jpg",
        "transfermarkt",
    ),
    "62b7529a-93ba-4000-96c5-4e106c540ae9": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657665/players/wonderkids/wk_62b7529a_rouven_tarnutzer.jpg",
        "transfermarkt",
    ),
    "6bd98eef-0e68-42cd-b862-1e1bee14a5fa": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657641/players/wonderkids/wk_6bd98eef_roy_snip.jpg",
        "transfermarkt",
    ),
    "6c477e5f-d60b-42fc-86bc-71afad1ac13e": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657870/players/wonderkids/wk_6c477e5f_ruan_pablo.png",
        "transfermarkt",
    ),
    "20ef1abc-5d8d-4f77-909f-5cb1dabf01dc": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/South european/Dark Brown/776.png",
        "gtex_regen_newgen_face_bank",
    ),
    "141f714a-9ab6-45e7-b10c-34251f565640": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/South european/Dark Brown/1039.png",
        "gtex_regen_newgen_face_bank",
    ),
    "32912936-7e0b-401e-a5dd-9610530c8bb1": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/South european/Dark Brown/319.png",
        "gtex_regen_newgen_face_bank",
    ),
    "5935c08e-47f1-4faf-b719-76384e963eee": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/North european/Dark Brown/Untitled-151 copy.png",
        "gtex_regen_newgen_face_bank",
    ),
    "663688f0-bf1b-4b23-a389-041840f162d7": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793658408/players/wonderkids/wk_663688f0_ryan_francisco.png",
        "migrated_to_cloudinary",
    ),
    "1123f605-bd13-4966-bad1-7629ec8d7e6b": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793658404/players/wonderkids/wk_1123f605_ryan_kavuma_mcqueen.jpg",
        "migrated_to_cloudinary",
    ),
    "bc754c3a-158d-44e0-9eae-949085699209": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/North european/Dark Brown/425.png",
        "gtex_regen_newgen_face_bank",
    ),
    "c1a2dddc-9b29-482f-ba06-0b39763830ba": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784995868/generated-media/regen_newgen_faces/script_skin_hair/Mixed/Dark%20Brown/africa-darkbrown-189.png",
        "gtex_regen_newgen_face_bank",
    ),
    "f460c17d-187a-47f8-9088-335878c372d9": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657785/players/wonderkids/wk_f460c17d_ryan_mcaidoo.jpg",
        "transfermarkt",
    ),
    "7d4b4ba6-17e6-4f4d-8efe-d319e4464dde": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657873/players/wonderkids/wk_7d4b4ba6_ryan_roberto.png",
        "transfermarkt",
    ),
    "6f31b032-bc8e-46a5-88be-b67144351075": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657865/players/wonderkids/wk_6f31b032_ryan_roberto.png",
        "transfermarkt",
    ),
    "1708da13-a58f-4283-8c7d-a7293054c13b": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/North european/Dark Brown/696.png",
        "gtex_regen_newgen_face_bank",
    ),
    "040121d5-7608-4f72-a667-bc3c4ad7c585": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657908/players/wonderkids/wk_040121d5_sadiki_chemwor.png",
        "transfermarkt",
    ),
    "b01045c8-4a49-48f1-8726-42b74a6bdee3": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/South european/Dark Brown/860.png",
        "gtex_regen_newgen_face_bank",
    ),
    "62db60ee-9276-44e7-b7b1-551da7113623": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/North european/Dark Brown/593.png",
        "gtex_regen_newgen_face_bank",
    ),
    "3b803221-709a-4047-9836-ff9392f4c9b2": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/North european/Dark Brown/454.png",
        "gtex_regen_newgen_face_bank",
    ),
    "75775cfa-ea27-4b4e-8522-ff6f521897f5": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657893/players/wonderkids/wk_75775cfa_sam_alabi.jpg",
        "transfermarkt",
    ),
    "f389fe62-57f9-4c43-ba7b-77b89634e7b0": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/South european/Dark Brown/945.png",
        "gtex_regen_newgen_face_bank",
    ),
    "c33d7324-0944-48c1-bbba-8fa19dad28ca": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657889/players/wonderkids/wk_c33d7324_sami_bouhoudane.jpg",
        "transfermarkt",
    ),
    "3db3d2fb-9243-420d-8daa-10f51d48fdf3": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/South european/Dark Brown/1129.png",
        "gtex_regen_newgen_face_bank",
    ),
    "fb84b10c-bb4a-41a7-9608-4f9d418adf6b": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793656344/players/wonderkids/wk_fb84b10c_samuel_friday_james.png",
        "sofifa_cloudinary",
    ),
    "97d693eb-947c-41b6-a9cf-830e264db6ff": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657892/players/wonderkids/wk_97d693eb_samuel_lusale.jpg",
        "transfermarkt",
    ),
    "e924130d-52cf-41bf-b58f-03a432d6c8a5": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657716/players/wonderkids/wk_e924130d_samuele_in_cio.jpg",
        "transfermarkt",
    ),
    "fdbcc1d1-2b10-419a-84a7-9abbae323ad2": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/North european/Dark Brown/820.png",
        "gtex_regen_newgen_face_bank",
    ),
    "b1b8c832-a97f-4d54-97b4-3b43f27af494": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657747/players/wonderkids/wk_b1b8c832_sander_ballero.png",
        "transfermarkt",
    ),
    "65a3d2b7-6243-4cb7-a691-32c552eb245b": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657826/players/wonderkids/wk_65a3d2b7_santiago_esp_ndola.jpg",
        "transfermarkt",
    ),
    "3cfe6414-481b-48fb-89d9-9dd199400f23": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657728/players/wonderkids/wk_3cfe6414_santiago_zampieri.png",
        "transfermarkt",
    ),
    "9d0af3dc-a64e-45cd-9ff8-d8eedee6fee1": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/Hispanic/Dark Brown/Untitled-149 copy.png",
        "gtex_regen_newgen_face_bank",
    ),
    "339c9c26-c4f9-4ef5-8b67-294f5eff9a3f": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/Middle east/Dark Brown/Untitled-162 copy.png",
        "gtex_regen_newgen_face_bank",
    ),
    "2ceb6db8-2519-4b03-88ef-eeab1c138c21": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657745/players/wonderkids/wk_2ceb6db8_sergi_mayans.jpg",
        "transfermarkt",
    ),
    "23c37349-7e97-474d-b758-8e3131fd29d9": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793656329/players/wonderkids/wk_23c37349_sergio_mart_nez.png",
        "sofifa_cloudinary",
    ),
    "54cc2945-f149-482f-be29-9868157629cf": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657666/players/wonderkids/wk_54cc2945_shea_lacey.jpg",
        "transfermarkt",
    ),
    "64f9f23b-7d45-4bf8-9754-eedb6198ea2d": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/African/Dark Brown/africa-darkbrown-75.png",
        "gtex_regen_newgen_face_bank",
    ),
    "fb12b7c7-cdef-4867-a791-f1b84c25495f": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/South european/Dark Brown/Untitled-119 copy.png",
        "gtex_regen_newgen_face_bank",
    ),
    "9f94b551-476a-47da-b927-e482d4828bfb": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/Mixed/Dark Brown/africa-darkbrown-13.png",
        "gtex_regen_newgen_face_bank",
    ),
    "0fc4f2c2-700c-485f-9265-b0f783175de9": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793659135/players/wonderkids/wk_0fc4f2c2_simeon_rapsch.webp",
        "transfermarkt_uploaded",
    ),
    "a9e5f0ed-0314-45c0-999e-412a8777afec": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997857/generated-media/regen_newgen_faces/script_skin_hair/African/Black/africa-black-129.png",
        "gtex_regen_newgen_face_bank",
    ),
    "6be73ed0-d631-4b6f-8c3d-2df350f6fd29": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793656342/players/wonderkids/wk_6be73ed0_sim_n_garc_a.png",
        "sofifa_cloudinary",
    ),
    "a7efa067-3994-4c74-b06f-3e7d3c5d2742": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657890/players/wonderkids/wk_a7efa067_spike_brits.jpg",
        "transfermarkt",
    ),
    "69dd556d-b9e7-440d-9808-0ba8458f9b16": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/North european/Dark Brown/484.png",
        "gtex_regen_newgen_face_bank",
    ),
    "b14e8cb2-d142-496e-91d0-065739a812b2": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/African/Dark Brown/africa-darkbrown-190.png",
        "gtex_regen_newgen_face_bank",
    ),
    "73777cf2-50e6-410a-bd93-45860b2a173d": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657735/players/wonderkids/wk_73777cf2_stephen_ireland.jpg",
        "transfermarkt",
    ),
    "3b61f519-5710-4bad-b4af-b300181767de": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657664/players/wonderkids/wk_3b61f519_stephen_mfuni.jpg",
        "transfermarkt",
    ),
    "922e0f62-c3da-412b-b77e-b44463e0e2e4": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657773/players/wonderkids/wk_922e0f62_stephen_michael.jpg",
        "transfermarkt",
    ),
    "a51ea258-5bc4-439b-b1dc-1fa2e540af5f": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657880/players/wonderkids/wk_a51ea258_steven_gerard_gaote.png",
        "transfermarkt",
    ),
    "01e72b86-9e86-429d-bce4-7add5529d08f": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657854/players/wonderkids/wk_01e72b86_stuart_holden.jpg",
        "transfermarkt",
    ),
    "eae0c0bf-e7ec-4d20-b6c8-4fb1f390a729": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657765/players/wonderkids/wk_eae0c0bf_suleman_sani.jpg",
        "transfermarkt",
    ),
    "3c53fdf4-3c80-4f7c-942a-a355542b3a86": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793658417/players/wonderkids/wk_3c53fdf4_sydney_osazuwa.png",
        "migrated_to_cloudinary",
    ),
    "f825bd86-ff93-4c85-813f-0122f69fa50c": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657750/players/wonderkids/wk_f825bd86_taha_emre_ince.png",
        "transfermarkt",
    ),
    "1b30715d-f248-4c66-840e-95c89c45fded": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657764/players/wonderkids/wk_1b30715d_tahir_maigana.jpg",
        "transfermarkt",
    ),
    "0cfe6400-6701-42a4-a0d5-e94c2cfc1ab1": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/African/Dark Brown/africa-darkbrown-192.png",
        "gtex_regen_newgen_face_bank",
    ),
    "d4bc4a09-f679-4227-8ca2-d2f20ecaaa28": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657753/players/wonderkids/wk_d4bc4a09_takashi_inui.jpg",
        "transfermarkt",
    ),
    "bf0c68d5-cc40-4e70-a2ea-39dfa7d7d62b": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657811/players/wonderkids/wk_bf0c68d5_taufik_seidu.jpg",
        "transfermarkt",
    ),
    "8335335d-b84b-435b-9abd-f6cc93dc9d22": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657804/players/wonderkids/wk_8335335d_taufik_seidu.jpg",
        "transfermarkt",
    ),
    "0776a47a-f51f-43af-9785-ca00330daf84": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657904/players/wonderkids/wk_0776a47a_tayo_subuloye.jpg",
        "transfermarkt",
    ),
    "9b747872-b6c6-452f-84f8-449a4cd45350": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/North european/Dark Brown/Untitled-85 copy.png",
        "gtex_regen_newgen_face_bank",
    ),
    "c960e75a-20ac-4f7f-a912-bc9d634debcf": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657793/players/wonderkids/wk_c960e75a_teo_rodr_guez_pagano.jpg",
        "transfermarkt",
    ),
    "38c83c45-f5ab-46b0-b3ed-dda75f6b47c6": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793656340/players/wonderkids/wk_38c83c45_terry_van_de_ven.png",
        "sofifa_cloudinary",
    ),
    "2b349f64-fa45-4680-b993-701938e4b011": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657860/players/wonderkids/wk_2b349f64_tevis.jpg",
        "transfermarkt",
    ),
    "fe9d6764-c9a6-431e-b837-c3062b9975e1": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657891/players/wonderkids/wk_fe9d6764_theo_julienne.jpg",
        "transfermarkt",
    ),
    "36c39e29-1139-4ae9-b32b-9e926db0b062": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/Hispanic/Dark Brown/Untitled-194 copy.png",
        "gtex_regen_newgen_face_bank",
    ),
    "06516707-9d1a-4236-a544-840b4afe5f3e": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657724/players/wonderkids/wk_06516707_thiago_ponce.png",
        "transfermarkt",
    ),
    "ab70d6d3-e3f1-4805-ae5e-4ff29ad334ce": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/Hispanic/Dark Brown/866.png",
        "gtex_regen_newgen_face_bank",
    ),
    "5fc808a9-9e83-457f-a879-536f993135a4": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/Hispanic/Dark Brown/519.png",
        "gtex_regen_newgen_face_bank",
    ),
    "61417133-564a-449d-bc61-1ed6318ec537": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/North european/Dark Brown/Untitled-77 copy.png",
        "gtex_regen_newgen_face_bank",
    ),
    "99e5bc3d-2687-469e-b801-8af705bfb006": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657760/players/wonderkids/wk_99e5bc3d_thomas_de_martis.jpg",
        "transfermarkt",
    ),
    "294bf4ca-674a-4b53-8861-2d287c5c3a78": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657755/players/wonderkids/wk_294bf4ca_thomas_de_martis.jpg",
        "transfermarkt",
    ),
    "eb42e80d-9ce4-4839-a3ce-f356defd0add": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/North european/Dark Brown/584.png",
        "gtex_regen_newgen_face_bank",
    ),
    "8b01df03-0a6d-417d-9e62-5a9ab97228e6": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657863/players/wonderkids/wk_8b01df03_tiaguinho.jpg",
        "transfermarkt",
    ),
    "c0214952-566c-4325-87b4-13138e96e3e6": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793658411/players/wonderkids/wk_c0214952_tidiane_diarrassouba.png",
        "migrated_to_cloudinary",
    ),
    "5f175760-f408-4fe3-b6db-d002bc440070": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/North european/Dark Brown/344.png",
        "gtex_regen_newgen_face_bank",
    ),
    "2d62580b-4b83-4183-9391-8028b9dd5d51": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/Hispanic/Dark Brown/781.png",
        "gtex_regen_newgen_face_bank",
    ),
    "216e82ef-fa90-4b4e-8918-ba6eb21bf209": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/Hispanic/Dark Brown/Untitled-133 copy.png",
        "gtex_regen_newgen_face_bank",
    ),
    "2cb13039-09c8-4b2a-8ae8-7e8ec142475b": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793658397/players/wonderkids/wk_2cb13039_tob_as_palacio.jpg",
        "migrated_to_cloudinary",
    ),
    "c4cfa5f1-ce8b-4893-9918-6c35d3125db0": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/North european/Dark Brown/271.png",
        "gtex_regen_newgen_face_bank",
    ),
    "010735fd-1a98-4654-8ccd-8e60928dd776": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/Mixed/Dark Brown/africa-darkbrown-219.png",
        "gtex_regen_newgen_face_bank",
    ),
    "89e398ba-ec83-496b-aaa1-731a5848503f": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/South european/Dark Brown/848.png",
        "gtex_regen_newgen_face_bank",
    ),
    "32abcbbe-77ef-4b9d-af3a-2bb274d49251": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657754/players/wonderkids/wk_32abcbbe_tom_s_parmo.png",
        "transfermarkt",
    ),
    "1510568c-7f91-45e8-847c-6f8c74dc8e35": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657832/players/wonderkids/wk_1510568c_tom_s_parmo.png",
        "transfermarkt",
    ),
    "d13ab5f2-8f96-44ee-ab42-8d4d728067dc": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793658399/players/wonderkids/wk_d13ab5f2_trevan_sanusi.png",
        "migrated_to_cloudinary",
    ),
    "7d96ad9f-2da7-4585-8df5-9ab6fc20d636": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/North european/Dark Brown/360.png",
        "gtex_regen_newgen_face_bank",
    ),
    "2d3d7ebf-072d-40e6-b209-ca284cc1e26b": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657628/players/wonderkids/wk_2d3d7ebf_tyrese_noubissie.jpg",
        "transfermarkt",
    ),
    "b7b3c007-2826-40ff-a672-404f6d479d67": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657805/players/wonderkids/wk_b7b3c007_ulrich_varens_fokam.jpg",
        "transfermarkt",
    ),
    "303a9d4d-f5f9-4281-b118-fd1dc66abe9d": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657774/players/wonderkids/wk_303a9d4d_umar_abubakar.jpg",
        "transfermarkt",
    ),
    "c9ddfa04-7e44-4018-b6be-89d3190367c4": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657723/players/wonderkids/wk_c9ddfa04_uriel_ojeda.jpg",
        "transfermarkt",
    ),
    "7d5f4331-1a68-4db1-bbed-a40fc6cef55d": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/North european/Dark Brown/1081.png",
        "gtex_regen_newgen_face_bank",
    ),
    "0b762537-fab2-4609-9a34-d27b67d24585": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/South european/Dark Brown/1206.png",
        "gtex_regen_newgen_face_bank",
    ),
    "ed454740-6cb4-4b50-97d9-7b396b9e8f9b": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657802/players/wonderkids/wk_ed454740_victory_akpe.png",
        "transfermarkt",
    ),
    "d6b82682-be93-4f2a-aa2e-2ccd43fd4ca1": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657682/players/wonderkids/wk_d6b82682_viggo_gebel.jpg",
        "transfermarkt",
    ),
    "f80db5d5-41f8-407b-a266-6ba2b2297763": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793659136/players/wonderkids/wk_f80db5d5_vince_osuji.webp",
        "transfermarkt_uploaded",
    ),
    "4a18af51-6724-4bb9-9eb4-fb6b5048de8f": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/North european/Dark Brown/612.png",
        "gtex_regen_newgen_face_bank",
    ),
    "1f55727c-0fff-448a-88ea-fdb2d595a1ee": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793656356/players/wonderkids/wk_1f55727c_vitor_hugo.png",
        "sofifa_cloudinary",
    ),
    "5b436412-0a19-44a4-bdc5-67ada11f3403": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793658416/players/wonderkids/wk_5b436412_vuyo_letlapa.png",
        "migrated_to_cloudinary",
    ),
    "ab457ad3-77b1-4f77-98a5-a2ad78000c57": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657805/players/wonderkids/wk_ab457ad3_vuyolwethu_andrieas.png",
        "transfermarkt",
    ),
    "158e322b-2580-43fd-b87a-feb8dc52c61a": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657842/players/wonderkids/wk_158e322b_wael_mohya.jpg",
        "transfermarkt",
    ),
    "aef2f68c-49b5-47a1-aa1e-2bef9985151a": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997992/generated-media/regen_newgen_faces/script_skin_hair/African/Blonde/africa-blonde-9.png",
        "gtex_regen_newgen_face_bank",
    ),
    "aa135fc1-c1da-45a0-8f7d-86241d2a931f": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/Mixed/Dark Brown/africa-darkbrown-235.png",
        "gtex_regen_newgen_face_bank",
    ),
    "0c9272e4-31eb-4ae3-aed6-a6ed1144fd30": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/Mixed/Dark Brown/africa-darkbrown-219.png",
        "gtex_regen_newgen_face_bank",
    ),
    "b162bc73-f940-4799-9cca-dc3c51c41458": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/Mixed/Dark Brown/africa-darkbrown-125.png",
        "gtex_regen_newgen_face_bank",
    ),
    "e2083128-19a4-4669-8449-2d06e42a9dde": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793658415/players/wonderkids/wk_e2083128_wisdom_mike.png",
        "migrated_to_cloudinary",
    ),
    "5aae175a-daef-43ea-bd52-810b0cef7fda": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/North european/Dark Brown/Untitled-47 copy.png",
        "gtex_regen_newgen_face_bank",
    ),
    "12e77390-9bd0-4653-b2f7-b05986f0bc59": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657854/players/wonderkids/wk_12e77390_yago_noal.jpg",
        "transfermarkt",
    ),
    "9cf02383-5921-49d9-a022-83c3bfbccf2d": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657637/players/wonderkids/wk_9cf02383_yahya_idrissi.jpg",
        "transfermarkt",
    ),
    "4a8e1b57-0727-4712-bfee-5599fd06a4c1": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657797/players/wonderkids/wk_4a8e1b57_yahya_idrissi_regragui.jpg",
        "transfermarkt",
    ),
    "94c2e9b9-29d7-4bc8-b99d-fc5ec80d75c2": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/North european/Dark Brown/Untitled-4 copy.png",
        "gtex_regen_newgen_face_bank",
    ),
    "bbf5d2cd-ce95-435e-adea-a365e75101e4": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/North european/Dark Brown/812.png",
        "gtex_regen_newgen_face_bank",
    ),
    "d05ebd94-194d-4b19-8302-3f886aec8c41": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/Mixed/Dark Brown/africa-darkbrown-69.png",
        "gtex_regen_newgen_face_bank",
    ),
    "b3788285-d5e2-440e-b965-dcf97c75fec7": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784998189/generated-media/regen_newgen_faces/script_skin_hair/African/Light%20Brown/africa-lightbrown-229.png",
        "gtex_regen_newgen_face_bank",
    ),
    "aacb1e6c-8087-445e-8cb2-e158edcdffa7": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657839/players/wonderkids/wk_aacb1e6c_yasir_boz.jpg",
        "transfermarkt",
    ),
    "a22de741-f933-441d-9ffa-e52928719151": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/African/Dark Brown/africa-darkbrown-232.png",
        "gtex_regen_newgen_face_bank",
    ),
    "598ae4c1-52aa-4c68-978c-05966e5e8b82": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657871/players/wonderkids/wk_598ae4c1_yeremaiah_ramos.jpg",
        "transfermarkt",
    ),
    "032970dc-8c58-47e6-a868-21f8792c403a": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657736/players/wonderkids/wk_032970dc_yll_gashi.jpg",
        "transfermarkt",
    ),
    "a6767f5d-d8b1-4b91-b0bf-8cd4be625a47": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657882/players/wonderkids/wk_a6767f5d_yoshinori_muto.jpg",
        "transfermarkt",
    ),
    "dea10ef9-f78e-429b-8e29-9f096244ddf0": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657675/players/wonderkids/wk_dea10ef9_younan_faghir_afghani.jpg",
        "transfermarkt",
    ),
    "5986fd77-8dd1-46c8-805d-1cdf279bf97f": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/Middle east/Dark Brown/Untitled-169 copy.png",
        "gtex_regen_newgen_face_bank",
    ),
    "34a8e4bb-e080-49c1-b091-6915b9545976": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793658418/players/wonderkids/wk_34a8e4bb_yunus_konak.png",
        "migrated_to_cloudinary",
    ),
    "3398509c-ce73-478d-9338-5c81b6c22b6b": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1784997839/generated-media/regen_newgen_faces/script_skin_hair/Middle east/Dark Brown/Untitled-130 copy.png",
        "gtex_regen_newgen_face_bank",
    ),
    "467add42-d11f-4688-b4d5-9858f3a953ff": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793658415/players/wonderkids/wk_467add42_zion_suzuki.png",
        "migrated_to_cloudinary",
    ),
    "5e8ea85f-e04d-495d-961f-4706f18bb185": (
        "https://res.cloudinary.com/dvxiniqew/image/upload/v1793657717/players/wonderkids/wk_5e8ea85f_ziyad_baha.jpg",
        "transfermarkt",
    ),
}


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())
    is_postgres = bind.dialect.name == "postgresql"

    if not is_postgres:
        return

    # Process in batches of 100 for optimal performance
    items = list(WONDERKID_PORTRAITS.items())
    batch_size = 100

    for i in range(0, len(items), batch_size):
        batch = items[i : i + batch_size]
        for pid, (url, src) in batch:
            safe_url = url.replace("'", "''")
            safe_src = src.replace("'", "''")

            # 1. Update ingestion_players dna_profile
            if "ingestion_players" in tables:
                dna_patch = json.dumps(
                    {
                        "portraitUrl": url,
                        "image_url": url,
                        "portraitStatus": "ready",
                        "portraitSourceProvider": src,
                    }
                ).replace("'", "''")

                op.execute(f"""
                    UPDATE ingestion_players
                    SET
                        dna_profile = (COALESCE(CAST(dna_profile AS jsonb), CAST('{{}}' AS jsonb)) || CAST('{dna_patch}' AS jsonb))::json,
                        updated_at = NOW()
                    WHERE id = '{pid}';
                """)

            # 2. Update ingestion_player_image_metadata
            if "ingestion_player_image_metadata" in tables:
                op.execute(f"""
                    DELETE FROM ingestion_player_image_metadata WHERE player_id = '{pid}' AND image_role = 'portrait';
                    INSERT INTO ingestion_player_image_metadata (
                        id, player_id, source_provider, provider_external_id,
                        image_role, source_url, moderation_status, rights_cleared,
                        is_primary, created_at, updated_at
                    ) VALUES (
                        gen_random_uuid(), '{pid}', '{safe_src}', '{pid}',
                        'portrait', '{safe_url}', 'approved', true,
                        true, NOW(), NOW()
                    );
                """)

            # 3. Update player_summary_read_models
            if "player_summary_read_models" in tables:
                summary_patch = json.dumps(
                    {
                        "image_url": url,
                        "portrait_url": url,
                        "portrait_status": "ready",
                    }
                ).replace("'", "''")

                op.execute(f"""
                    UPDATE player_summary_read_models
                    SET
                        summary_json = (COALESCE(CAST(summary_json AS jsonb), CAST('{{}}' AS jsonb)) || CAST('{summary_patch}' AS jsonb))::json,
                        updated_at = NOW()
                    WHERE player_id = '{pid}';
                """)


def downgrade() -> None:
    pass
