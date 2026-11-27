import type {Tree} from './types'

type Metric = 'power_w' | 'water_pct' | 'oxygen_flow_lph' | 'temperature_c' | 'humidity_pct'

export function latestMetric(tree:Tree|null, field:Metric) {
  const sensor=tree?.latest_sensors, reading=tree?.latest
  if(sensor && sensor[field]!=null && (reading?.[field]==null || Date.parse(sensor.time)>=Date.parse(reading.time))) {
    return sensor[field]
  }
  return reading?.[field] ?? tree?.prototype_estimates?.[field] ?? null
}

export function latestTime(tree:Tree|null) {
  const a=tree?.latest?.time, b=tree?.latest_sensors?.time
  if(!a)return b
  if(!b)return a
  return Date.parse(a)>Date.parse(b)?a:b
}
