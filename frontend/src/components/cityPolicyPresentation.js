// Display permissions only. Never acquisition/source approval or a fact registry.
import {CITIES} from '../config/cities';
import {officialKyotoUrl,policyPresentation,policyProgress} from './kyotoPolicyPresentation';

export function officialCityUrl(city, value) {
  const hosts=CITIES[city]?.mayorDisplayHosts || [];
  try {
    const url=new URL(value);
    const authority=typeof value==='string' ? value.match(/^https:\/\/([^/?#]+)/)?.[1] : null;
    return url.protocol==='https:' && hosts.includes(authority) && url.hostname===authority &&
      !url.username && !url.password && !url.port ? url.href : null;
  } catch { return null; }
}

export function cityPresentation(city) {
  if(city==='kyoto') return {cityName:'京都市',officialUrl:officialKyotoUrl,
    presentation:policyPresentation,progress:policyProgress};
  const config=CITIES[city];
  return {
    cityName:config?.fullName || '対象都市',
    officialUrl:value=>officialCityUrl(city,value),
    presentation:p=>({title:p.headline || p.id,status:p.latest_update?.kind==='construction_paused' ? '停止情報あり' : '根拠を確認中',
      warning:p.progress_evidence?.status==='hold' ? '登録された根拠は保留中です。議決成立・実施を認定しません。'
        : '各資料と政策の対応を確認中です。登録段階は達成済みを意味しません。',
      // A document's purpose is explicit; choosing the pledge is not confirmation.
      source:!p.election_promise?.is_broken && officialCityUrl(city,p.election_promise?.bulletin_url)
        ? {url:p.election_promise.bulletin_url,label:'登録公約の原文（確認状態は詳細へ）'} : null}),
    progress:p=>{
      // Never run Kyoto ID exceptions for a foreign city's P-01/P-02/P-03.
      const result=policyProgress({...p,id:'',latest_update:undefined,progress_evidence:undefined});
      if(p.progress_evidence?.status==='hold') Object.assign(result.steps[3],{state:'hold',note:'議案等の対応を確認中です。可決済みと認定しません。'});
      if(p.latest_update?.kind==='construction_paused') Object.assign(result.steps[4],{state:'paused',note:'停止に関する登録情報があります。再開や開始時期は原典と確認状態をご覧ください。'});
      return result;
    },
  };
}
