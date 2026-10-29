import { 
  NAGOYA_VALID_COUNCILORS, 
  getNagoyaCouncilorMasterInfo 
} from './nagoyaCouncilorMaster';
import { 
  COUNCILOR_MASTER as KYOTO_COUNCILOR_MASTER, 
  getCouncilorMasterInfo as getKyotoCouncilorInfo 
} from './councilorMaster';

import { 
  OSAKA_VALID_COUNCILORS, 
  getOsakaCouncilorMasterInfo 
} from './osakaCouncilorMaster';

const KYOTO_VALID_COUNCILORS = Object.keys(KYOTO_COUNCILOR_MASTER || {});

/**
 * 都市コードに応じて有効な議員名リストを取得
 */
export function getValidCouncilors(cityCode) {
  if (cityCode === 'yokohama') return [];
  if (cityCode === 'nagoya') {
    return Array.isArray(NAGOYA_VALID_COUNCILORS) ? NAGOYA_VALID_COUNCILORS : [];
  }
  if (cityCode === 'osaka') {
    return Array.isArray(OSAKA_VALID_COUNCILORS) ? OSAKA_VALID_COUNCILORS : [];
  }
  if (cityCode === 'kyoto') {
    return KYOTO_VALID_COUNCILORS;
  }
  return [];
}

/**
 * 都市コードと議員名から、所属会派や選挙区等のマスタ情報を取得
 */
export function getCouncilorInfo(cityCode, speakerName) {
  if (!speakerName) return {};
  if (cityCode === 'yokohama') return {};
  if (!speakerName) return {};
  if (cityCode === 'nagoya') {
    const info = typeof getNagoyaCouncilorMasterInfo === 'function'
      ? getNagoyaCouncilorMasterInfo(speakerName)
      : {};
    return {
      ...info,
      party: info.party || info.faction || '',
      partyGroup: info.partyGroup || info.faction || ''
    };
  }
  if (cityCode === 'osaka') {
    return typeof getOsakaCouncilorMasterInfo === 'function' 
      ? getOsakaCouncilorMasterInfo(speakerName) 
      : {};
  }
  if (cityCode === 'kyoto') {
    return typeof getKyotoCouncilorInfo === 'function' 
      ? getKyotoCouncilorInfo(speakerName) 
      : {};
  }
  return {};
}
