import pydantic
import asyncpg
from gino import Gino
from aiohttp import web

PG_DSN = f'postgres://aiohttp:1234@db:5430/aiohttp'

app = web.Application()
db = Gino()


class ModelMixin:

    @classmethod
    async def create_instance(cls, *args, **kwargs):
        try:
            return (await cls.create(*args, **kwargs))
        except asyncpg.exceptions.UniqueViolationError:
            raise web.HTTPBadRequest


class AdvertisementModel(db.Model, ModelMixin):

    __tablename__ = 'advertisement'

    id = db.Column(db.Integer(), primary_key=True)
    title = db.Column(db.String(100))
    description = db.Column(db.Text())

    _idx1 = db.Index('app_advs_id', 'id', unique=True)


class AdvertisementSerializer(pydantic.BaseModel):
    title: str
    description: str


class Advertisement(web.View):

    async def post(self):
        data = await self.request.json()
        adv_serialized = AdvertisementSerializer(**data)
        data = adv_serialized.dict()
        new_adv = await AdvertisementModel.create_instance(**data)
        return web.json_response(new_adv.to_dict())

    async def get(self):
        adv_id = self.request.match_info['adv_id']
        adv = await AdvertisementModel.get(int(adv_id))
        if adv:
            adv_data = adv.to_dict()
            return web.json_response(adv_data)
        else:
            raise web.HTTPNotFound

    async def delete(self):
        adv_id = self.request.match_info['adv_id']
        adv = await AdvertisementModel.get(int(adv_id))
        if adv:
            await adv.delete()
            return web.json_response({'status': 'ok'}, status=200)
        else:
            raise web.HTTPNotFound


async def init_orm(app):
    await db.set_bind(PG_DSN)
    await db.gino.create_all()

    yield

    await db.pop_bind().close()


app.add_routes([web.post('/adv', Advertisement)])
app.add_routes([web.get('/adv/{adv_id:\d+}', Advertisement)])
app.add_routes([web.delete('/adv/{adv_id:\d+}', Advertisement)])
app.cleanup_ctx.append(init_orm)

web.run_app(app, port=8080)
