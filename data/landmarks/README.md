# Mongolia destination catalog

113 sourced destinations supplement the 42 legacy places: **155 places in total**.
The catalog covers major domestic and international visitor destinations across
Mongolia: monasteries, lakes, mountains, parks, archaeological sites, museums,
waterfalls, hot springs and travel gateways. It is a maintained selection, not an
exhaustive registry of every attraction, campsite or local place name.

## Files and coordinate meaning

- `catalog.json`: reviewed additions with Mongolian/English names and short descriptions,
  aliases, aimag, GeoJSON `[longitude, latitude]` and coordinate provenance.
- `aliases.json`: extra search names for 13 existing places. Their IDs, coordinates,
  routes and commercial inventory remain unchanged.
- `../mock/places.json`: generated combined catalog consumed by the existing seed pipeline.
  Sourced additions are marked `is_mock: false`; this does not make nearby mock stays,
  prices or availability real.

Each addition records `coordinate_source.url`, `source_id`, `retrieved_on` and
`coordinate_role`. `landmark` means the location of a specific feature or building;
`representative_point` means a map point for a larger area, lake or park. Neither
means a verified vehicle entrance, campsite or navigable road endpoint. Map centers
and published coordinates have different precision; decimal digits do not guarantee
survey accuracy. Broad or cross-border features have one representative aimag, not
a complete list of administrative areas they span. `fuel_available: false` means
no fuel availability was verified for the addition.

Sources include Wikidata P625, published Wikipedia coordinates, UNESCO listings,
OpenStreetMap features displayed by Mapcarta, and a destination map published by
Steppe Mongolia. Wikidata API throttling prevented using P625 for every location;
records retain the actual source used, without labelling alternate sources as Wikidata.
OSM-derived coordinates are © [OpenStreetMap contributors](https://www.openstreetmap.org/copyright)
and are available under ODbL. Source links and OSM feature IDs are preserved below
and in JSON. Descriptions are short original summaries, not copied article text.

## Updating and loading

1. Edit `catalog.json` (or add an existing place's names to `aliases.json`). Verify
   the exact feature, aimag and coordinate from a public source; keep a stable ID.
   Include both languages and aliases, particularly common Latin transliterations.
2. Run `python3 data/mock/generate.py` from the repository root. This is offline and
   deterministic; it does not fetch sources or reshuffle the mock inventory.
3. Run the catalog, resolver and planner tests, then `make seed` to update the
   configured database. Normal seed preserves bookings, payments and inventory;
   `make seed-reset` replaces runtime data and is unnecessary for this update.

The resolver searches names and aliases, prefers an exact name over a partial
match, and keeps province/region requests broad. Nearby stays use the existing
60 km search. Additional road routes, accommodation and bookable inventory are not
created by adding a destination; missing road routes retain the planner's estimated
distance behavior. The legacy region polygons are approximate display geometry,
so new destinations use their reviewed aimag to assign a region.

## Sourced additions

Coordinates below are latitude, longitude for human reading; JSON uses longitude,
latitude. Every row links to the actual coordinate source (checked 2026-09-30).

| Аймаг / хот | Монгол нэр | English name | Latitude, longitude | Source |
| --- | --- | --- | --- | --- |
| Arkhangai | Чулуутын хавцал | Chuluut River Gorge | 48.1322667, 100.2736667 | [Chuluut Gorge and river](https://www.spanglefish.com/gowildernessmongolia/gpsreferences.asp) |
| Arkhangai | Хангайн нурууны байгалийн цогцолборт газар | Khangai Nuruu National Park | 47.2, 101.4 | [Khangai_Nuruu_National_Park](https://en.wikipedia.org/wiki/Khangai_Nuruu_National_Park) |
| Arkhangai | Хорго | Khorgo | 48.1863889, 99.8552778 | [Q2462320](https://www.wikidata.org/wiki/Q2462320) |
| Arkhangai | Хар балгас | Ordu-Baliq | 47.43111, 102.65944 | [Ordu-Baliq](https://en.wikipedia.org/wiki/Ordu-Baliq) |
| Arkhangai | Орхоны хөндий | Orkhon Valley | 47.55667, 102.83139 | [Orkhon_Valley](https://en.wikipedia.org/wiki/Orkhon_Valley) |
| Arkhangai | Хөшөө Цайдам | Orkhon inscriptions | 47.56056, 102.84111 | [Orkhon_inscriptions](https://en.wikipedia.org/wiki/Orkhon_inscriptions) |
| Arkhangai | Суварга хайрхан | Suvaraga Khairkhan | 47.05611, 101.36583 | [Suvraga_Khairkhan](https://en.wikipedia.org/wiki/Suvraga_Khairkhan) |
| Arkhangai | Тайхар чулуу | Taikhar Rock | 47.6, 101.283 | [Taikhar_Rock](https://en.wikipedia.org/wiki/Taikhar_Rock) |
| Arkhangai | Цэнхэрийн халуун рашаан | Tsenkher hot spring | 47.319917, 101.6485 | [Tsenkher_Hot_Spring](https://en.wikipedia.org/wiki/Tsenkher_Hot_Spring) |
| Arkhangai | Өгий нуур | Ögii Lake | 47.7608333, 102.7672222 | [Q2000570](https://www.wikidata.org/wiki/Q2000570) |
| Bayan-Ölgii | Бага Түргэний хүрхрээ | Baga Turgen waterfall | 48.5071111, 88.3609722 | [Q133270705](https://www.wikidata.org/wiki/Q133270705) |
| Bayan-Ölgii | Хотон нуур | Khoton Lake | 48.65, 88.3 | [Khoton_Lake](https://en.wikipedia.org/wiki/Khoton_Lake) |
| Bayan-Ölgii | Хурган нуур | Khurgan Lake | 48.54611, 88.60611 | [Khurgan_Lake](https://en.wikipedia.org/wiki/Khurgan_Lake) |
| Bayan-Ölgii | Хүйтэн оргил | Khüiten Peak | 49.14583, 87.81889 | [Khüiten_Peak](https://en.wikipedia.org/wiki/Kh%C3%BCiten_Peak) |
| Bayan-Ölgii | Монгол Алтайн хадны зургийн цогцолбор | Petroglyphic Complexes of the Mongolian Altai | 49.3338889, 88.3952778 | [Q4361429](https://www.wikidata.org/wiki/Q4361429) |
| Bayan-Ölgii | Потанины мөсөн гол | Potanin Glacier | 49.14, 87.92 | [Potanin_Glacier](https://en.wikipedia.org/wiki/Potanin_Glacier) |
| Bayan-Ölgii | Толбо нуур | Tolbo Lake | 48.56, 90.05 | [Tolbo_Lake](https://en.wikipedia.org/wiki/Tolbo_Lake) |
| Bayan-Ölgii | Цамбагарав | Tsambagarav | 48.68167, 90.725 | [Tsambagarav](https://en.wikipedia.org/wiki/Tsambagarav) |
| Bayankhongor | Бөөн Цагаан нуур | Böön Tsagaan Lake | 45.5961111, 99.1419444 | [Q749776](https://www.wikidata.org/wiki/Q749776) |
| Bayankhongor | Их Богд | Ikh Bogd | 44.995, 100.23083 | [Ikh_Bogd](https://en.wikipedia.org/wiki/Ikh_Bogd) |
| Bayankhongor | Орог нуур | Orog Lake | 45.055, 100.70472 | [Orog_Lake](https://en.wikipedia.org/wiki/Orog_Lake) |
| Bayankhongor | Шаргалжуутын халуун рашаан | Shargaljuut Hot Springs | 46.3324167, 101.2260278 | [Shargaljuut spring N1, Table 1](https://pangea.stanford.edu/ERE/pdf/IGAstandard/NZGW/2003/Bignall.pdf) |
| Bayankhongor | Цагаан агуй | Tsagaan Agui | 44.712028, 101.170389 | [Tsagaan_Agui](https://en.wikipedia.org/wiki/Tsagaan_Agui) |
| Bulgan | Хөгнө хан | Khogno Khan National Park | 47.47, 103.64 | [Q93828284](https://www.wikidata.org/wiki/Q93828284) |
| Dornod | Буйр нуур | Buir Lake | 47.80694, 117.69222 | [Buir_Lake](https://en.wikipedia.org/wiki/Buir_Lake) |
| Dornod | Их Бурхант | Ikh Burkhant | 47.87365, 118.45153 | [OSM way 912989688](https://mapcarta.com/W912989688) |
| Dornod | Халхголын ялалтын хөшөө | Khalkhgol Victory Monument | 47.63485, 118.5990667 | [Yalaltiin Khoshuu GPS](https://www.lonelyplanet.com/points-of-interest/yalaltiin-khoshuu/1454351) |
| Dornod | Халхын гол | Khalkhyn Gol | 47.89556, 117.83556 | [Khalkhyn_Gol](https://en.wikipedia.org/wiki/Khalkhyn_Gol) |
| Dornod | Монгол Дагуур | Mongol Daguur | 49.7, 115.1 | [Mongol_Daguur](https://en.wikipedia.org/wiki/Mongol_Daguur) |
| Dornod | Нөмрөгийн дархан цаазат газар | Nömrög National Park | 47.0, 119.5 | [Numrug, p98](https://portals.iucn.org/library/sites/library/files/documents/PAPS-011.pdf) |
| Dornogovi | Данзанравжаагийн музей | Danzanravjaa Museum | 44.892794, 110.139355 | [Danzanravjaa_Museum](https://en.wikipedia.org/wiki/Danzanravjaa_Museum) |
| Dornogovi | Их Нартын чулуу | Ikh Nartiin Chuluu Nature Reserve | 45.567, 108.633 | [Ikh_Nartiin_Chuluu_Nature_Reserve](https://en.wikipedia.org/wiki/Ikh_Nartiin_Chuluu_Nature_Reserve) |
| Dornogovi | Хамарын хийд | Khamar Monastery | 44.5972167, 110.2734806 | [Khamar_Monastery](https://en.wikipedia.org/wiki/Khamar_Monastery) |
| Dornogovi | Хан Баянзүрх уул | Khan Bayanzurkh | 44.69227, 110.04444 | [OSM way 1498438002](https://mapcarta.com/W1498438002) |
| Dundgovi | Бага газрын чулуу | Baga Gazaryn Chuluu | 46.1988, 106.03074 | [OSM way 199162313](https://mn.geoview.info/baga_gazriin_chuluu%2C199162313w) |
| Dundgovi | Их газрын чулуу | Ikh Gazriin Chuluu | 45.75, 107.25 | [MN049, p71](https://cdn.greensoft.mn/uploads/users/366/files/Key%20Sites%20for%20Conservation.pdf) |
| Dundgovi | Онгийн хийд | Ongi Monastery | 45.3398083, 104.004278 | [Ongi_Monastery](https://en.wikipedia.org/wiki/Ongi_Monastery) |
| Dundgovi | Сүм Хөх Бүрд | Sum Khukh Burd | 46.15472, 105.76014 | [OSM node 3774871391](https://mapcarta.com/N3774871391) |
| Govi-Altai | Бурхан буудай | Burkhan Buudai | 45.67472, 96.75028 | [Burkhan_Buudai](https://en.wikipedia.org/wiki/Burkhan_Buudai) |
| Govi-Altai | Ээж хайрхан | Eej Khairkhan | 44.9437, 96.2171 | [OSM way 552847517](https://mapcarta.com/W552847517) |
| Govi-Altai | Хасагт хайрхан | Khasagt Khairkhan | 46.78917, 95.80083 | [Khasagt_Khairkhan](https://en.wikipedia.org/wiki/Khasagt_Khairkhan) |
| Govi-Altai | Шаргын говь | Sharga Nature Reserve | 46, 94.5 | [Sharga_Nature_Reserve](https://en.wikipedia.org/wiki/Sharga_Nature_Reserve) |
| Govisümber | Чойрын Богд | Choir Bogd | 46.2143056, 108.7673278 | [Choiriin Bogd mountain](https://whc.unesco.org/en/tentativelists/6817/) |
| Khentii | Аваргын балгас | Avraga | 47.09444, 109.15278 | [Avraga](https://en.wikipedia.org/wiki/Avraga) |
| Khentii | Балдан Бэрээвэн хийд | Baldan Bereeven Monastery | 48.2024389, 109.4390028 | [Baldan_Bereeven_Monastery](https://en.wikipedia.org/wiki/Baldan_Bereeven_Monastery) |
| Khentii | Бурхан Халдун | Burkhan Khaldun | 48.7619601, 109.0102959 | [Burkhan_Khaldun](https://en.wikipedia.org/wiki/Burkhan_Khaldun) |
| Khentii | Дэлүүн Болдог | Delüün Boldog | 49.02167, 111.62472 | [Delüün_Boldog](https://en.wikipedia.org/wiki/Del%C3%BC%C3%BCn_Boldog) |
| Khentii | Хан Хэнтийн дархан цаазат газар | Khan Khentii Strictly Protected Area | 48.92, 108.59 | [Khan_Khentii_Strictly_Protected_Area](https://en.wikipedia.org/wiki/Khan_Khentii_Strictly_Protected_Area) |
| Khentii | Хар зүрхний Хөх нуур | Khar Zurkhnii Khukh Nuur | 48.0175817, 108.9464717 | [Khökh Nuur coronation site GPS](https://www.lonelyplanet.com/points-of-interest/khoekh-nuur/1405861) |
| Khentii | Хөдөө арал | Khuduu Aral | 47.180722, 109.059667 | [UNESCO tentative list 5952](https://whc.unesco.org/en/tentativelists/5952) |
| Khentii | Онон-Балжийн байгалийн цогцолборт газар | Onon-Balj National Park | 48.98, 111.1 | [Onon-Balj_National_Park](https://en.wikipedia.org/wiki/Onon-Balj_National_Park) |
| Khovd | Дөргөн нуур | Dörgön Lake | 47.7, 93.417 | [Dörgön_Lake](https://en.wikipedia.org/wiki/D%C3%B6rg%C3%B6n_Lake) |
| Khovd | Ховдын Хар нуур | Khar Lake (Khovd) | 48.08, 93.2 | [Khar_Lake_(Khovd)](https://en.wikipedia.org/wiki/Khar_Lake_%28Khovd%29) |
| Khovd | Хойд Цэнхэрийн агуй | Khoit Tsenkher Cave | 47.3473611, 91.9566944 | [Khoit Tsenkheriin cave](https://www.mongoliancave.com/CaveEng/2) |
| Khovd | Мөнххайрхан уул | Mönkhkhairkhan Mountain | 46.89, 91.47333 | [Mönkhkhairkhan_Mountain](https://en.wikipedia.org/wiki/M%C3%B6nkhkhairkhan_Mountain) |
| Khövsgöl | Дархадын хотгор | Darkhad Valley | 51.167, 99.5 | [Darkhad_Valley](https://en.wikipedia.org/wiki/Darkhad_Valley) |
| Khövsgöl | Ханх | Khankh | 51.51167, 100.65361 | [Khankh,_Khövsgöl](https://en.wikipedia.org/wiki/Khankh%2C_Kh%C3%B6vsg%C3%B6l) |
| Khövsgöl | Хорьдол Сарьдаг | Khoridol Saridag mountains | 50.6894, 99.7922 | [Khoridol_Saridag_mountains](https://en.wikipedia.org/wiki/Khoridol_Saridag_mountains) |
| Khövsgöl | Хөвсгөл нуур | Lake Khövsgöl | 51.1, 100.5 | [Lake_Khövsgöl](https://en.wikipedia.org/wiki/Lake_Kh%C3%B6vsg%C3%B6l) |
| Khövsgöl | Мөнх Сарьдаг | Mönkh Saridag | 51.71889, 100.61472 | [Mönkh_Saridag](https://en.wikipedia.org/wiki/M%C3%B6nkh_Saridag) |
| Khövsgöl | Рэнчинлхүмбэ | Renchinlkhümbe | 51.10861, 99.67083 | [Renchinlkhümbe](https://en.wikipedia.org/wiki/Renchinlkh%C3%BCmbe) |
| Khövsgöl | Сангийн далай нуур | Sangiin Dalai Lake | 49.25, 99 | [Sangiin_Dalai_Lake](https://en.wikipedia.org/wiki/Sangiin_Dalai_Lake) |
| Khövsgöl | Цагааннуур | Tsagaannuur, Khövsgöl | 51.35444, 99.35333 | [Tsagaannuur,_Khövsgöl](https://en.wikipedia.org/wiki/Tsagaannuur%2C_Kh%C3%B6vsg%C3%B6l) |
| Khövsgöl | Уушгийн өвөр | Uushgiin Övör | 49.655139, 99.9275 | [Deer stones at Uushgiin Uvur 01 camera location](https://commons.wikimedia.org/wiki/File:Deer_stones_at_Uushgiin_Uvur_01.jpg) |
| Selenge | Алтанбулаг | Altanbulag, Selenge | 50.31667, 106.49417 | [Altanbulag,_Selenge](https://en.wikipedia.org/wiki/Altanbulag%2C_Selenge) |
| Selenge | Ээж мод | Eej Mod | 50.1540283, 106.2015217 | [Eej Mod GPS](https://www.lonelyplanet.com/points-of-interest/eej-mod/1462248) |
| Selenge | Сайханы хөтөл | Saikhany Khutul | 50.30861, 106.15414 | [OSM node 4896343922](https://mapcarta.com/N4896343922) |
| Selenge | Тужийн нарс | Tujiin Nars | 50.1, 106.4 | [Tujiin Nars](https://en.wikipedia.org/wiki/List_of_national_parks_of_Mongolia) |
| Sükhbaatar | Алтан овоо | Altan Ovoo | 45.31136, 113.83553 | [Dari Ovoo](https://mapcarta.com/16411588) |
| Sükhbaatar | Ганга нуур | Ganga Lake | 45.26709, 113.98582 | [OSM way 200578959](https://mapcarta.com/W200578959) |
| Sükhbaatar | Талын агуй | Taliin Agui | 45.5902778, 114.5005722 | [Taliin cave](https://mongoliancave.com/CaveEng/1) |
| Töv | Аглаг бүтээлийн хийд | Aglag Buteel Monastery | 48.44885, 106.12264 | [OSM way 1549618003](https://mapcarta.com/de/W1549618003) |
| Töv | Арьяабалын сүм | Aryabal Meditation Temple | 47.93552, 107.42742 | [OSM way 247465544](https://mapcarta.com/W247465544) |
| Töv | Асралт хайрхан | Asralt Khairkhan | 48.46556, 107.41278 | [Asralt_Khairkhan](https://en.wikipedia.org/wiki/Asralt_Khairkhan) |
| Töv | Чингис хааны морьт хөшөө | Equestrian statue of Genghis Khan | 47.8080556, 107.52975 | [Equestrian_statue_of_Genghis_Khan](https://en.wikipedia.org/wiki/Equestrian_statue_of_Genghis_Khan) |
| Töv | Горхи-Тэрэлж | Gorkhi-Terelj National Park | 48.150204, 107.576006 | [Gorkhi-Terelj_National_Park](https://en.wikipedia.org/wiki/Gorkhi-Terelj_National_Park) |
| Töv | Гүнжийн сүм | Gunjiin Sum | 48.1835, 107.5562833 | [Gunjiin Sum GPS](https://www.lonelyplanet.com/points-of-interest/gunjiin-sum/498964) |
| Töv | Хагийн Хар нуур | Khagiin Khar Lake | 48.4103, 107.9118 | [OSM way 50158686](https://mapcarta.com/W50158686) |
| Töv | Хустайн нуруу | Khustain Nuruu National Park | 47.765, 105.87833 | [Khustain_Nuruu_National_Park](https://en.wikipedia.org/wiki/Khustain_Nuruu_National_Park) |
| Töv | Манзушир хийд | Manjusri Monastery | 47.76444, 106.99222 | [Manjusri_Monastery](https://en.wikipedia.org/wiki/Manjusri_Monastery) |
| Töv | Зоргол хайрхан | Zorgol Khairkhan | 46.92332, 105.87832 | [OSM node 2381057453](https://mapcarta.com/N2381057453) |
| Ulaanbaatar | Богд хан уул | Bogd Khan Mountain | 47.80389, 106.98639 | [Bogd_Khan_Mountain](https://en.wikipedia.org/wiki/Bogd_Khan_Mountain) |
| Ulaanbaatar | Чингис хаан үндэсний музей | Chinggis Khaan National Museum | 47.922528, 106.914917 | [Chinggis_Khaan_National_Museum](https://en.wikipedia.org/wiki/Chinggis_Khaan_National_Museum) |
| Ulaanbaatar | Чойжин ламын сүм музей | Choijin Lama Temple | 47.915, 106.91833 | [Choijin_Lama_Temple](https://en.wikipedia.org/wiki/Choijin_Lama_Temple) |
| Ulaanbaatar | Гандантэгчэнлин хийд | Gandantegchinlen Monastery | 47.92306, 106.895 | [Gandantegchinlen_Monastery](https://en.wikipedia.org/wiki/Gandantegchinlen_Monastery) |
| Ulaanbaatar | Монголын үндэсний музей | National Museum of Mongolia | 47.9208, 106.9154 | [National_Museum_of_Mongolia](https://en.wikipedia.org/wiki/National_Museum_of_Mongolia) |
| Ulaanbaatar | Сүхбаатарын талбай | Sükhbaatar Square | 47.91889, 106.9175 | [Sükhbaatar_Square](https://en.wikipedia.org/wiki/S%C3%BCkhbaatar_Square) |
| Ulaanbaatar | Мэлхий хад | Turtle Rock Mongolia | 47.9074, 107.4229 | [OSM node 280751202](https://mapcarta.com/N280751202) |
| Ulaanbaatar | Богд хааны ордон музей | Winter Palace of the Bogd Khan | 47.8975, 106.90667 | [Winter_Palace_of_the_Bogd_Khan](https://en.wikipedia.org/wiki/Winter_Palace_of_the_Bogd_Khan) |
| Ulaanbaatar | Зайсан толгой | Zaisan Memorial | 47.88417, 106.91583 | [Zaisan_Memorial](https://en.wikipedia.org/wiki/Zaisan_Memorial) |
| Ulaanbaatar | Занабазарын нэрэмжит дүрслэх урлагийн музей | Zanabazar Museum of Fine Arts | 47.9201944, 106.9096944 | [Q2370206](https://www.wikidata.org/wiki/Q2370206) |
| Uvs | Ачит нуур | Achit Lake | 49.5, 90.5 | [Achit_Lake](https://en.wikipedia.org/wiki/Achit_Lake) |
| Uvs | Хархираа уул | Kharkhiraa | 49.56972, 91.38528 | [Kharkhiraa](https://en.wikipedia.org/wiki/Kharkhiraa) |
| Uvs | Хэцүү хад | Khetsuu Khad | 49.03505, 93.47703 | [OSM node 11506787269](https://mapcarta.com/N11506787269) |
| Uvs | Хяргас нуур | Khyargas Lake | 49.133, 93.417 | [Khyargas_Lake](https://en.wikipedia.org/wiki/Khyargas_Lake) |
| Uvs | Үүрэг нуур | Üüreg Lake | 50.167, 91 | [Üüreg_Lake](https://en.wikipedia.org/wiki/%C3%9C%C3%BCreg_Lake) |
| Zavkhan | Завханы Баян нуур | Bayan Lake | 48.456, 95.118 | [Bayan_Lake](https://en.wikipedia.org/wiki/Bayan_Lake) |
| Zavkhan | Улаагчны Хар нуур | Khar Lake (Zavkhan) | 48.35, 96.1 | [Khar_Lake_(Zavkhan)](https://en.wikipedia.org/wiki/Khar_Lake_%28Zavkhan%29) |
| Zavkhan | Мухартын гол | Mukhart River | 48.210264, 95.941884 | [Mukhartyn gol embedded Google map center](https://www.steppe-mongolia.com/discover-mongolia/destinations/mukhart_river_zavkhan) |
| Zavkhan | Отгонтэнгэр | Otgontenger | 47.60833, 97.5525 | [Otgontenger](https://en.wikipedia.org/wiki/Otgontenger) |
| Zavkhan | Сэнжит хад | Senjit Khad | 48.21555, 96.14864 | [OSM way 1446949824](https://mapcarta.com/W1446949824) |
| Zavkhan | Тэлмэн нуур | Telmen Lake | 48.833, 97.317 | [Telmen_Lake](https://en.wikipedia.org/wiki/Telmen_Lake) |
| Ömnögovi | Бүгийн цав | Bügiin Tsav | 43.88115, 100.0273167 | [Bugin Tsav GPS](https://cfile214.uf.daum.net/attach/27106A3357DB9FD22DBCBB) |
| Ömnögovi | Говь Гурвансайхан | Gobi Gurvansaikhan National Park | 43.802729, 101.589663 | [Gobi_Gurvansaikhan_National_Park](https://en.wikipedia.org/wiki/Gobi_Gurvansaikhan_National_Park) |
| Ömnögovi | Хэрмэн цав | Khermen Tsav | 43.4667667, 99.8329333 | [Khermen Tsav GPS](https://www.lonelyplanet.com/points-of-interest/khermen-tsav/1406657) |
| Ömnögovi | Нэмэгтийн хотгор | Nemegt Basin | 43.5, 101 | [Nemegt_Basin](https://en.wikipedia.org/wiki/Nemegt_Basin) |
| Övörkhangai | Эрдэнэ Зуу хийд | Erdene Zuu Monastery | 47.2016667, 102.8433333 | [Q1058965](https://www.wikidata.org/wiki/Q1058965) |
| Övörkhangai | Хархорумын туурь | Karakorum | 47.21028, 102.84778 | [Karakorum](https://en.wikipedia.org/wiki/Karakorum) |
| Övörkhangai | Хархорум музей | Kharakhorum Museum | 47.195307, 102.83928 | [Kharakhorum_Museum](https://en.wikipedia.org/wiki/Kharakhorum_Museum) |
| Övörkhangai | Хүйсийн найман нуур | Naiman Nuur | 46.5589, 101.8103 | [Huisiin naiman nuur, p18](https://mrt.gov.mn/up/news/BodlogoTululvlult/%D0%A5%D0%B0%D0%B2%D1%81%D1%80%D0%B0%D0%BB%D1%828.pdf) |
| Övörkhangai | Улаан цутгалан | Orkhon waterfall | 46.78725, 101.96025 | [Q4470791](https://www.wikidata.org/wiki/Q4470791) |
| Övörkhangai | Шанх хийд | Shankh Monastery | 47.0514, 102.954 | [Q1630910](https://www.wikidata.org/wiki/Q1630910) |
| Övörkhangai | Төвхөн хийд | Tövkhön Monastery | 47.01221, 102.25499 | [Q7857142](https://www.wikidata.org/wiki/Q7857142) |
