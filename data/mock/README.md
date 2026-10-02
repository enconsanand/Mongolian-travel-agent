# Монгол аяллын mock өгөгдөл

Өгөгдлийн сангийн бүрэн тайлбар (монгол + англи, schema, collection бүр): [docs/DATABASE.md](../../docs/DATABASE.md)

Буудал, захиалга, үнэ, утас, арга хэмжээний огноо зэрэг нь **mock**. Газрын жагсаалтад эх сурвалжтай координат бүхий 113 бодит газар нэмэгдсэн (`is_mock: false`); дэлгэрэнгүй жагсаалт, эх сурвалж, шинэчлэх заавар нь [landmarks/README.md](../landmarks/README.md)-д бий. MongoDB-ийн collection бүрт нэг JSON массив. Id-ууд string бөгөөд файлууд хооронд холбогдоно. Үнэ бүгд MNT.

## Collection-ууд

| Файл | Тоо | Юу байгаа |
|---|---|---|
| regions.json | 4 | Хойд, баруун, зүүн, өмнөд бүс: аймгийн жагсаалт, ойролцоо GeoJSON polygon, `min_days`, `best_months`, онцлох газрууд |
| places.json | 268 | Хот, сум, үзвэр; нэрийн хувилбарууд (`aliases`), шинэ газрын координатын эх сурвалж (`coordinate_source`). Улаанбаатар = `region: "hub"` (эхлэх цэг) |
| routes.json | 25 | Замын хэсгүүд: км, жолоодох минут, хучилт (paved/mixed/dirt), аюул, LineString. `area` = хуучин дэд бүс (khuvsgul, gobi...) |
| events.json | 36 | Аймгийн наадам, Бүргэдийн баяр, Мөсний баяр, Мянган тэмээний баяр, жижиг арга хэмжээ |
| stays.json | 105 | Гэр кемп, зочид буудал, гэр буудал, байшин, малчин айл. `images` (3 зураг), `cover_image_url` |
| translations.mn.json | 242 | Өгөгдлийн англи текстийн монгол орчуулга (collection биш) |
| images.json | 58 | Газар, буудал, арга хэмжээ тус бүрийн бодит зураг (Wikimedia Commons). `fetch_images.py` үүсгэнэ (collection биш) |
| image_pool.json | 37 | Буудлын төрөл бүрийн ерөнхий зураг; ойролцоо зураг олдоогүй буудлыг дүүргэнэ (collection биш) |
| cancellation_policies.json | 4 | flexible / moderate / strict / deposit_only |
| stay_availability.json | 3774 | Буудал, өрөөний төрөл, өдөр бүрээр (2026-07-01 → 2026-10-31). Зарим кемп `closed_for_season` |
| supplemental_catalog.data | — | Нэмэлт газар, эвент, буудал болон сул орны өгөгдөл; `generate.py` үндсэн каталогоос тусад нь нэгтгэнэ (collection биш) |
| drivers.json | 16 | Жолооч, хэл, `regions_served` |
| vehicles.json | 29 | Автобус, UAZ фургон, Land Cruiser, Prius. `rental.mode`: `with_driver` эсвэл `self_drive` (барьцаа, даатгал, км лимит) |
| vehicle_availability.json | 322 | Түрээсийн машин өдөр бүр сул/захиалгатай/засвартай |
| transport_schedules.json | 55 | Автобус, галт тэрэг (УБ→Дархан→Сүхбаатар, УБ→Эрдэнэт, УБ→Чойр→Сайншанд→Замын-Үүд), онгоц, хамтын фургон; буцах болон хот хоорондын чиглэлтэй |
| transport_availability.json | 1142 | Хөдлөх өдөр, цаг, суудлын ангилал бүрээр үлдсэн суудал |
| shared_rides.json | 12 | Хамтын унаа: жолооч суудал зардаг (`driver_offer`) эсвэл хувь хүн машинаа хуваалцдаг (`traveler_post`) |
| users.json | 3 | Anand, Tsendayush, Jambaa. Хадгалсан карт (зөвхөн token + сүүлийн 4 орон) + QPay |
| app_config.json | 1 | Шатахууны үнэ (AI-92, AI-95, дизель). Машин бүр `fuel_type`, `fuel_l_per_100km`-тэй |
| audit_log.json | 20 | Агент, хэрэглэгч, эзний үйлдэл бүр (төлбөрийн алхам бүр) — зөвхөн нэмнэ, засахгүй |
| conversations.json | 1 | Jambaa-гийн агенттай ярьсан түүх (tool_calls-тэй) |
| agent_state.json | 1 | Агент аль алхамд байгаа, бөглөсөн slot-ууд, хүлээгдэж буй зөвшөөрөл |
| user_memory.json | 2 | Хэрэглэгчийн урт хугацааны сонголт ("өөрөө машин барих дуртай") |
| trips.json, itinerary_versions.json | 5 / 6 | Хөвсгөлийн хувилбар солигдох демо, Говь, мөн 3 хэрэглэгчийн аялал (баруун, хойд, зүүн) |
| quotes.json | 6 | Агентын санал болгосон хувилбарууд (хэрэглэгч аль нэгийг сонгоно) |
| bookings.json | 24 | Буудал, тээвэр, машин түрээс, хамтын унаа, тасалбар |
| payments.json | 7 | Төлбөрийн төлөв: `quoted → approved_by_user → paid → cancelled → refunded`, `status_history`, `consent`, `idempotency_key` |
| refunds.json | 1 | Жолооч цуцалсан хамтын унааны буцаалт |

## Нэвтрэх хэрэглэгчид ба карт

- 3 хэрэглэгч: `anand@nashatech.com`, `tsendayush@nashatech.com`, `jambaa@nashatech.com`.
- Нууц үг **энд хадгалагдаагүй**. Backend seed (`back/app/seeds/datas/users.json`, `user_seed.py`) нь `SEED_DEV_PASSWORD` орчны хувьсагчаас нууц үгийг авна. Тохируулаагүй бол санамсаргүй нууц үг үүсгээд log-д хэвлэнэ.
- Картын дугаар, CVC-г **хадгалдаггүй**: зөвхөн Stripe test token (`pm_card_visa`), brand, сүүлийн 4 орон. Checkout-ийн маягтад Stripe-ийн туршилтын дугаарууд: Anand 4242 4242 4242 4242, Tsendayush 4012 8888 8888 1881, Jambaa 4000 0566 5566 5556 (дурын ирээдүйн огноо, дурын CVC). Жинхэнэ мөнгө татахгүй.

## Schema

- Collection бүрийн бүтэц `back/app/schemas/travel.py`-д (Pydantic). Энэ нь цорын ганц эх сурвалж.
- `make seed` нь document бүрийг schema-аар шалгаад, collection-ыг MongoDB `$jsonSchema` validator-тай үүсгэнэ (`back/app/db/validators.py`). Буруу бүтэцтэй document MongoDB-д орохгүй.
- Шинэ талбар нэмбэл: `generate.py` → `schemas/travel.py` → `python3 generate.py` → `make seed`.

## API (`/api/v1`, `Accept-Language: mn|en`)

`/regions`, `/regions/locate?lng&lat`, `/places`, `/stays` (`region`, `type`, `lng`+`lat`+`radius_km`, `date`), `/stays/{id}`, `/routes`, `/events` (`date_from`, `date_to`), `/cancellation-policies`, `/transport/schedules`, `/transport/availability`, `/shared-rides`, `/vehicles` (`rental_mode`, `date`), `/drivers`, `/config/fuel`, нэвтэрсэн хэрэглэгчид: `/me/trips`, `/me/trips/{id}`, `/me/payments`. Дэлгэрэнгүйг `/docs`-оос.

## Хоёр хэл (mn / en)

- Хүн уншдаг бүх текст (нэр, тайлбар, тэмдэглэл, маршрутын summary, аяллын гарчиг...) `{"mn": "...", "en": "..."}` хэлбэртэй.
- Код утгууд (`type`, `status`, `amenities`, `hazards`, `surface`...) код хэвээрээ. Эдгээрийн дэлгэцэнд харагдах нэрийг front өөрөө орчуулна.
- Mock текстийн монгол орчуулга `translations.mn.json`-д байна. `generate.py` шинэ англи текст орчуулгагүй байвал алдаа заана. Шинэ бодит газруудын хоёр хэлний нэр, тайлбар `../landmarks/catalog.json`-д шууд хадгалагдана.
- Backend `Accept-Language` header-ээс хэлийг аваад (`app/utils/i18n.py`, default `mn`) `localize(doc, lang)`-оор нэг хэл рүү хөрвүүлнэ.

## Зураг

- Бүх зураг Wikimedia Commons-оос, зөвхөн CC BY / CC BY-SA / CC0 / public domain. Зураг бүрт `author`, `license`, `source` байгаа тул дэлгэцэнд зохиогчийг заавал харуулна (CC BY-ийн нөхцөл).
- `match`: `location` — тухайн газрын 10 км дотор авсан зураг; `near_stay` — буудлын 5 км дотор авсан кемп/зочид буудлын зураг; `event_topic` — тухайн арга хэмжээний өмнөх жилийн бодит зураг; `type` — буудлын төрлийн ерөнхий зураг.
- Буудлууд зохиомол тул яг тэр буудлын зураг биш (`is_illustrative: true`). Resort, booking сайтын зургийг зохиогчийн эрхийн улмаас ашиглаагүй.
- Шинэчлэх: `python3 fetch_images.py` (интернэт хэрэгтэй, Commons удаан хариулдаг) → `python3 generate.py`.

## Бүсийн дүрэм

- Бүсийг аймгаар тодорхойлно. Polygon нь газрын зураг ба `$geoIntersects`-д зориулсан ойролцоо хүрээ, албан ёсны хил биш.
- Улаанбаатар бүс биш, `hub`. Төв, Архангай, Өвөрхангай хойд бүсэд орно.
- УБ-аас гарах маршрут, хуваарь, хамтын унаа нь очих газрынхаа бүсийг авна.

## Ачаалах

Газрын жагсаалтыг шинэчлэхдээ репогийн үндсэн хавтсаас `python3 data/mock/generate.py`, дараа нь `make seed` ажиллуулна. Энгийн seed нь одоо байгаа аялал, захиалга, төлбөр, сул орны үлдэгдлийг хадгална.

Бүх өгөгдлийг солих хуучин import скрипт:

```bash
MONGO_URI="mongodb+srv://..." ./import.sh
```

Бүх collection-ийг устгаад дахин ачаалж, 2dsphere болон хайлтын индексүүдийг үүсгэнэ.

Үндсэн өгөгдлийг өөрчлөх бол `generate.py`-г, нэмэлт каталогио өөрчлөх бол `supplemental_catalog.data`-г засаад `python3 generate.py` ажиллуулна. Анхны хойд/өмнөд өгөгдөл тусдаа RNG-тэй тул яг хэвээрээ үлдэнэ. Зай, цагийг геометрээс тооцдог.

## Жишээ query

```js
// Хатгалаас 30 км дотор байгаа буудал
db.stays.find({location: {$near: {$geometry: {type: "Point", coordinates: [100.16, 50.4425]}, $maxDistance: 30000}}})
// Цэг аль бүсэд байгааг олох
db.regions.findOne({boundary: {$geoIntersects: {$geometry: {type: "Point", coordinates: [89.96, 48.97]}}}})
// Баруун бүсийн нээлттэй буудлууд
db.stays.find({region: "west", "season.year_round": true})
// 10/3-нд УБ → Дархан галт тэрэгний сул купе
db.transport_availability.find({schedule_id: "sched_train_ub_sukhbaatar", date: "2026-10-03", seat_class: "kupe", seats_left: {$gt: 0}})
// Өөрөө жолоодох, 10/9-нд сул машин
db.vehicle_availability.aggregate([
  {$match: {date: "2026-10-09", status: "available"}},
  {$lookup: {from: "vehicles", localField: "vehicle_id", foreignField: "_id", as: "v"}},
  {$match: {"v.rental.mode": "self_drive"}}
])
// Хэрэглэгчийн батлахыг хүлээж буй төлбөр
db.payments.find({user_id: "user_jamba", status: {$in: ["quoted", "approved_by_user"]}})
```
