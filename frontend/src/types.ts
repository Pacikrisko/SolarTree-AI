export type Role = 'municipality' | 'owner'
export type Page = 'overview' | 'trees' | 'detail' | 'insights' | 'assistant' | 'service' | 'settings' | 'profile' | 'admin'
export interface User { id: number; name: string; email: string; role: Role; is_admin?:boolean; has_password:boolean }
export interface Reading { id:number; tree_id:number; time:string; power_w:number; temperature_c:number; humidity_pct:number; h2_sensor_value:number; water_pct:number; source:'simulation'|'device'; oxygen_flow_lph:number|null; electrolyzer_power_w:number|null; oxygen_basis:'simulation'|'measured'|'unavailable'|'estimated' }
export interface TreeConfig { code:string; name:string; panel_count:number; tilt_deg:number; rated_solar_w:number; description:string; auxiliary_kw?:number; electrolyzer_kw?:number; oxygen_nominal_lph?:number; fuel_cell_kw?:number; water_tank_l?:number; hydrogen_tank_l?:number }
export interface UrbanSimulation {
  battery_pct:number;
  hydrogen_pressure_bar_g:number; fuel_cell_load_kw:number; hydrogen_flow_nlph:number; mq8_adc_raw:number
}
export interface Tree { simulation?:UrbanSimulation|null; id:number; code:string; name:string; kind:'municipal'|'private'; model:TreeConfig; location:string; lat:number|null; lng:number|null; latest:Reading|null; open_alerts:number; service_attention:number; connection:'live'|'model'|'offline'; media_kind:'image'|'video'|null; latest_sensors?:{time:string;temperature_c:number|null;humidity_pct:number|null;mq8_adc_raw:number|null;power_w:number|null;water_pct:number|null;oxygen_flow_lph:number|null}|null }
export interface Alert { id:number; tree_id:number; tree_name:string; message:string; severity:string; acknowledged:boolean; time:string; can_ack:boolean }
export interface Service { id:number; tree_id:number; tree_name:string; component:'water_filter'|'oxygen_dryer'; label:string; last_service:string; due_at:string; days_left:number; status:'overdue'|'soon'|'ok'; interval_days:number; basis:'calendar' }
export interface Forecast { points:{time:string;power_w:number}[]; mae_w:number|null; trained_samples:number; model:string; synthetic_data?:boolean; disclaimer?:string }
export interface ChatMessage { role:'user'|'assistant'; content:string; mode?:string }
export interface TokenPayload { access_token:string; user:User }
export interface Health { ok:boolean; real_llm:boolean; ai_provider?:'cloudflare'|'openai'|null; simulation_enabled:boolean; version:string }

export interface PairResult { code:string; model:TreeConfig; kind:'municipal'|'private' }
export interface OxygenPoint { time:string; oxygen_flow_lph:number; cumulative_l:number; basis:string; source:string }
export interface OxygenHistory { tree_id:number; points:OxygenPoint[]; total_l:number; current_flow_lph:number|null; basis:string; note:string }

export interface PairSessionStart {id:number;url:string|null;qr_data_uri:string|null;expires_at:string;needs_https:boolean}
export interface PairSessionStatus {status:'pending'|'completed'|'expired';tree_id:number|null;tree_name:string|null;model:string|null}

export interface ResourceEstimate {
  water_capacity_l:number;water_fill_pct:number;water_available_l:number;
  water_consumption_lph:number;water_runtime_hours:number|null;
  hydrogen_tank_internal_l:number;hydrogen_pressure_bar_g:number|null;
  hydrogen_usable_normal_l:number|null;fuel_cell_load_kw:number;
  fuel_cell_efficiency:number;fuel_cell_hydrogen_consumption_nlph:number;
  hydrogen_runtime_hours:number|null;standard_conditions:string;basis:string
}

export interface ChatExchange { id:number; tree_id:number|null; question:string; reply:string; mode:'llm'|'report'; model:string|null; created_at:string }
