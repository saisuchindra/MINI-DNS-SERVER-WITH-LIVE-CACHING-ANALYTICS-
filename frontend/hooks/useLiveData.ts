"use client";
import { useCallback,useEffect,useState } from "react";
import { api } from "@/lib/api";
import type { Analytics,DNSResult,SocketEvent } from "@/lib/types";
export function useLiveData(){
 const [analytics,setAnalytics]=useState<Analytics|null>(null),[queries,setQueries]=useState<DNSResult[]>([]),[connected,setConnected]=useState(false),[error,setError]=useState<string|null>(null);
 const refresh=useCallback(async()=>{try{setAnalytics(await api.summary());setError(null)}catch(e){setError(e instanceof Error?e.message:"Backend unavailable")}},[]);
 useEffect(()=>{queueMicrotask(()=>void refresh());const ws=new WebSocket(process.env.NEXT_PUBLIC_WS_URL??"ws://127.0.0.1:8000/ws/analytics");ws.onopen=()=>setConnected(true);ws.onclose=()=>setConnected(false);ws.onerror=()=>setError("WebSocket disconnected");ws.onmessage=e=>{const m=JSON.parse(e.data) as SocketEvent;if(m.event==="analytics_update")setAnalytics(m.data as Analytics);if(m.event==="dns_query")setQueries(v=>[m.data as DNSResult,...v].slice(0,40));};return()=>ws.close()},[refresh]);
 return {analytics,queries,connected,error,refresh,setQueries};
}
