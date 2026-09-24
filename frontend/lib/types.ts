export type CacheStatus = "HIT" | "MISS";
export interface Health { status:string; dns_server:string; dns_error?:string|null; cache:string; database:string; simulation:string }
export interface Analytics { total_queries:number; successful_queries:number; failed_queries:number; cache_hits:number; cache_misses:number; hit_ratio:number; miss_ratio:number; queries_per_second:number; cache_entries:number; cache_utilization:number; cache_evictions:number; expired_entries:number; avg_latency_ms:number; min_latency_ms:number; max_latency_ms:number; udp_queries:number; tcp_queries:number }
export interface DNSResult { query_id:string; timestamp:string; domain:string; record_type:string; status:CacheStatus; source:string; ip_addresses:string[]; ttl:number; protocol:string; response_time_ms:number; flow:string[]; result_status:string; error?:string }
export interface CacheEntry { domain:string; record_type:string; ttl:number; original_ttl:number; ip_addresses:string[]; hits:number; created_at:string; expires_at:string; last_accessed:string; status:string }
export interface DomainStat { domain:string; query_count:number; hit_count:number; miss_count:number }
export interface LogEntry { id:string; timestamp:string; domain:string; record_type:string; protocol:string; cache_status:CacheStatus; response_source:string; response_time_ms:number; status:string; simulation_mode:number }
export interface SimConfig { interval_ms?:number; speed?:"slow"|"normal"|"fast"; real_dns?:boolean; record_type?:string; maximum_queries?:number|null; domain_distribution?:Record<string,number> }
export interface Simulation { status:"running"|"paused"|"stopped"; query_count:number; config:Required<SimConfig> }
export interface SocketEvent { event:"dns_query"|"analytics_update"|"simulation_status"|"error"; data: DNSResult|Analytics|Simulation|{message:string} }
