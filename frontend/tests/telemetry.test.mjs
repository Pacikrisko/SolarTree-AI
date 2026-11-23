import assert from 'node:assert/strict'
import test from 'node:test'
import { latestMetric, latestTime } from '../src/telemetry.ts'

test('latest partial and full readings agree on zero, missing values and timestamp', () => {
  const full = { time: '2026-11-23T10:03:00Z', power_w: 0, water_pct: 67 }
  const sensor = { time: '2026-11-23T10:00:00Z', power_w: 100, oxygen_flow_lph: 12 }
  const tree = { latest: full, latest_sensors: sensor }
  assert.equal(latestMetric(tree, 'power_w'), 0)
  assert.equal(latestMetric(tree, 'oxygen_flow_lph'), 12)
  assert.equal(latestTime(tree), full.time)
  sensor.time = '2026-11-23T10:05:00Z'
  assert.equal(latestMetric(tree, 'power_w'), 100)
  assert.equal(latestMetric(tree, 'water_pct'), 67)
  assert.equal(latestTime(tree), sensor.time)
  assert.equal(latestMetric(null, 'power_w'), null)
})
