import os
from aiohttp import web
from iaqualink.client import AqualinkClient
from iaqualink.device import (
  AqualinkBinarySensor,
  AqualinkLight,
  AqualinkPump,
  AqualinkSensor,
  AqualinkThermostat,
  AqualinkToggle,
  AqualinkHeater,
  AqualinkAuxToggle,
  AqualinkColorLight,
)
from prometheus_client import Gauge, Enum, CONTENT_TYPE_LATEST, generate_latest

spa_temp = Gauge('iaqualink_spa_temp', 'Description of gauge', ['system'])
pool_temp = Gauge('iaqualink_pool_temp', 'Description of gauge', ['system'])
air_temp = Gauge('iaqualink_air_temp', 'Description of gauge', ['system'])

spa_temp_target = Gauge('iaqualink_spa_temp_target', 'Description of gauge', ['system'])
pool_temp_target = Gauge('iaqualink_pool_temp_target', 'Description of gauge', ['system'])

spa_pump = Enum('iaqualink_spa_pump', 'Whether or not the Spa pump is running', ['system'], states=['running', 'stopped'])
spa_jet_pump = Enum('iaqualink_spa_jet_pump', 'Whether or not the Spa jet pump is running', ['system'], states=['running', 'stopped'])
pool_pump = Enum('iaqualink_pool_pump', 'Whether or not the Pool pump is running', ['system'], states=['running', 'stopped'])
pool_cleaner_pump = Enum('iaqualink_pool_cleaner_pump', 'Whether or not the Pool cleaner is running', ['system'], states=['running', 'stopped'])

pool_light = Enum('iaqualink_pool_light', 'Whether or not the Pool light is on', ['system'], states=['on', 'off'])
spa_light = Enum('iaqualink_spa_light', 'Whether or not the Spa light is on', ['system'], states=['on', 'off'])

spa_heater = Enum('iaqualink_spa_heater', 'Whether or not the Spa is heating', ['system'], states=['running', 'stopped'])
pool_heater = Enum('iaqualink_pool_heater', 'Whether or not the Pool is heating', ['system'], states=['running', 'stopped'])
solar_heater = Enum('iaqualink_solar_heater', 'Whether or not the Pool is being heated by Solar heater', ['system'], states=['running', 'stopped'])

iaqualink_user = os.environ.get('IAQUALINK_USERNAME')
iaqualink_password = os.environ.get('IAQUALINK_PASSWORD')

async def login():
  async with AqualinkClient(iaqualink_user, iaqualink_password) as c:
      s = await c.get_systems()
      for system in s.values():
        d = await system.get_devices()
        for device in d.values():
          if device.state.strip() == "":
            continue

          if isinstance(device, AqualinkThermostat):
            if device.name == "spa_set_point":
              spa_temp_target.labels(system=system.name).set(float(device.state))
            elif device.name == "pool_set_point":
              pool_temp_target.labels(system=system.name).set(float(device.state))
          elif isinstance(device, AqualinkLight):
            pass
          elif isinstance(device, AqualinkBinarySensor):
            pass
          elif isinstance(device, AqualinkPump) or isinstance(device, AqualinkHeater):
            enum = {
              "spa_pump": spa_pump,
              "pool_pump": pool_pump,
              "spa_heater": spa_heater,
              "pool_heater": pool_heater,
              "solar_heater": solar_heater,
            }
            pump = enum[device.name]
            if not pump:
              continue

            if device.is_on:
              pump.labels(system=system.name).state('running')
            else:
              pump.labels(system=system.name).state('stopped')
          elif isinstance(device, AqualinkSensor):
            if device.name == "spa_temp":
              spa_temp.labels(system=system.name).set(float(device.state))
            elif device.name == "pool_temp":
              pool_temp.labels(system=system.name).set(float(device.state))
            elif device.name == "air_temp":
              air_temp.labels(system=system.name).set(float(device.state))
          elif isinstance(device, AqualinkColorLight):
            enums = {
              "Pool Light": pool_light,
              "Spa Light": spa_light,
            }
            light = enums.get(device.label)
            if not light:
              continue

            if device.is_on:
              light.labels(system=system.name).state('on')
            else:
              light.labels(system=system.name).state('off')
          elif isinstance(device, AqualinkAuxToggle):
            enums = {
              "Cleaner": pool_cleaner_pump,
              "Jet Pump": spa_jet_pump,
            }
            pump = enums.get(device.label)
            if not pump:
              continue

            if device.is_on:
              pump.labels(system=system.name).state('running')
            else:
              pump.labels(system=system.name).state('stopped')
          elif isinstance(device, AqualinkToggle):
            pass

async def root(request):
    return web.Response(text='iaqualink_exporter')

async def metrics(request):
    await login()
    resp = web.Response(body=generate_latest())
    resp.content_type = CONTENT_TYPE_LATEST
    return resp

app = web.Application()
app.router.add_get('/metrics', metrics)
app.router.add_get('/', root)

if __name__ == '__main__':
    web.run_app(app, port=8080)
