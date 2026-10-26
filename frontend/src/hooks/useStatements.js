import { getValidCouncilors, getCouncilorInfo } from '../utils/councilorMasterAdapter';
import { getCityDataUrl } from '../config/cities';
import { useState, useEffect, useMemo } from 'react';
import { createClient } from '@supabase/supabase-js';
import MiniSearch from 'minisearch';
import { VALID_COUNCILORS, cleanName, determineCouncilorStyle } from '../utils/styleHelpers';

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL || '';
const supabaseKey = import.meta.env.VITE_SUPABASE_ANON_KEY || '';
const supabase = (supabaseUrl && supabaseKey) ? createClient(supabaseUrl, supabaseKey) : null;

function getDailyRandomGenerator() {
  const todayStr = new Date().toISOString().slice(0, 10);
  let h = 0;
  for (let i = 0; i < todayStr.length; i++) {
    h = Math.imul(31, h) + todayStr.charCodeAt(i) | 0;
  }
  return function () {
    h = Math.imul(h ^ (h >>> 16), 2246822507);
    h = Math.imul(h ^ (h >>> 13), 3266489909);
    return ((h ^= h >>> 16) >>> 0) / 4294967296;
  };
}

function shuffleWithDailySeed(array) {
  const rng = getDailyRandomGenerator();
  const arr = [...array];
  for (let i = arr.length - 1; i > 0; i--) {
    const j = Math.floor(rng() * (i + 1));
    [arr[i], arr[j]] = [arr[j], arr[i]];
  }
  return arr;
}

export function useStatements(cityCode = 'kyoto') {
  const [statements, setStatements] = useState([]);
  const [isLoading, setIsLoading] = useState(true);

  const [searchQuery, setSearchQuery] = useState('');
  const [submittedQuery, setSubmittedQuery] = useState('');

  const [selectedCategory, setSelectedCategory] = useState('');
  const [selectedCommittee, setSelectedCommittee] = useState('');
  const [selectedDistrict, setSelectedDistrict] = useState('');
  const [sortPerspective, setSortPerspective] = useState('random');
  const [viewMode, setViewMode] = useState('speakers');

  const [selectedSpeaker, setSelectedSpeaker] = useState(null);
  const [speakerCategory, setSpeakerCategory] = useState('');
  const [speakerSort, setSpeakerSort] = useState('recent');

  const [selectedContext, setSelectedContext] = useState(null);
  const [isPanelOpen, setIsPanelOpen] = useState(false);
  const [isLoadingContext, setIsLoadingContext] = useState(false);

  const [compareList, setCompareList] = useState([]);
  const [isCompareMode, setIsCompareMode] = useState(false);
  const [initialRouteSet, setInitialRouteSet] = useState(false);

  const [miniSearch] = useState(
    new MiniSearch({
      fields: ['summary', 'meeting_title', 'speaker', 'category'],
      storeFields: ['id', 'speaker'],
      searchOptions: { fuzzy: 0.2, prefix: true }
    })
  );

  useEffect(() => {
    if (!cityCode) {
      setStatements([]);
      setIsLoading(false);
      return;
    }
    fetchStatements();
  }, [cityCode]);

  const fetchStatements = async () => {
    setIsLoading(true);
    let allRecords = [];

    try {
      try {
        const prefix = cityCode === 'kyoto' ? '' : `${cityCode}_`;
        const res = await fetch(`/data/${prefix}statements_summary.json`);
        if (res.ok) {
          const text = await res.text();
          if (text.trim().startsWith('[') || text.trim().startsWith('{')) {
            allRecords = JSON.parse(text);
            console.log(`[useStatements] 静的JSONより ${allRecords.length} 件を取得しました。`);
          }
        }
      } catch (jsonErr) {
        console.warn('[useStatements] 静的JSON取得エラー:', jsonErr);
      }

      if ((!allRecords || allRecords.length === 0) && supabase) {
        console.log('[useStatements] Supabaseからデータ取得を開始...');
        try {
          let page = 0; const pageSize = 1000; let hasMore = true;
          while (hasMore) {
            const { data, error } = await supabase
              .from('statements')
              .select('*')
              .eq('is_evaluated', true)
              .range(page * pageSize, (page + 1) * pageSize - 1)
              .order('meeting_date', { ascending: false });
            if (error) throw error;
            if (data && data.length > 0) {
              allRecords = [...allRecords, ...data];
              if (data.length < pageSize) hasMore = false; else page += 1;
            } else { hasMore = false; }
          }
        } catch (supaErr) {
          console.error('[useStatements] Supabase取得エラー:', supaErr);
        }
      }

      if (!Array.isArray(allRecords)) allRecords = [];

      const validData = [];
      const seenIds = new Set();

      allRecords.forEach((stmt, idx) => {
        if (!stmt) return;
        const rawSpeaker = stmt.speaker || '';
        const speakerName = cleanName ? cleanName(rawSpeaker) : rawSpeaker;

        if (cityCode === 'kyoto' && VALID_COUNCILORS && Array.isArray(VALID_COUNCILORS)) {
          if (!VALID_COUNCILORS.includes(speakerName) && !VALID_COUNCILORS.includes(rawSpeaker)) return;
        }
        if (cityCode === 'osaka' && OSAKA_VALID_COUNCILORS && Array.isArray(OSAKA_VALID_COUNCILORS)) {
          if (!OSAKA_VALID_COUNCILORS.includes(speakerName) && !OSAKA_VALID_COUNCILORS.includes(rawSpeaker)) return;
        }

        const ev = Number(stmt.evidence_score || 0);
        const sol = Number(stmt.solution_score || 0);
        const lf = Number(stmt.local_focus_score || 0);
        const cons = Number(stmt.constructive_score || 0);
        const cat = stmt.category ? String(stmt.category).replace(/[\[\]'"]/g, '') : "政策質疑";

        if (cat.includes("進行") || (ev === 0 && sol === 0 && lf === 0 && cons === 0)) return;

        let docId = stmt.id != null ? String(stmt.id) : `local_${idx}`;
        if (seenIds.has(docId)) docId = `${docId}_${idx}`;
        seenIds.add(docId);

        validData.push({
          ...stmt,
          id: docId,
          speaker: rawSpeaker,
          category: cat,
          evidence_score: ev,
          solution_score: sol,
          local_focus_score: lf,
          constructive_score: cons
        });
      });

      try {
        miniSearch.removeAll();
        if (validData.length > 0) miniSearch.addAll(validData);
      } catch (msErr) {
        console.warn('[useStatements] MiniSearch warning:', msErr);
      }

      setStatements(validData);
    } catch (err) {
      console.error('[useStatements] fetchStatements critical error:', err);
    } finally {
      setIsLoading(false);
    }
  };

  const topicStats = useMemo(() => {
    if (statements.length === 0) return [];
    const counts = {};
    statements.forEach((s) => {
      const cats = (s.category || '').split(',').map((c) => c.trim()).filter(Boolean);
      cats.forEach((c) => { counts[c] = (counts[c] || 0) + 1; });
    });
    const total = Object.values(counts).reduce((a, b) => a + b, 0);
    return Object.entries(counts)
      .map(([name, count]) => ({ name, count, percentage: total > 0 ? ((count / total) * 100).toFixed(1) : 0 }))
      .sort((a, b) => b.count - a.count)
      .slice(0, 8);
  }, [statements, cityCode]);

  const speakerStats = useMemo(() => {
    const stats = {};
    statements.forEach((stmt) => {
      const spk = stmt.speaker;
      if (!stats[spk]) {
        const masterInfo = getCouncilorInfo(cityCode, spk);
        stats[spk] = {
          speaker: spk, count: 0,
          evidence_score: 0, solution_score: 0, local_focus_score: 0, constructive_score: 0,
          statements: [], catCounts: {}, latest_date: stmt.meeting_date || "",
          ...masterInfo
        };
      }
      const s = stats[spk];
      s.count += 1;
      s.evidence_score += stmt.evidence_score;
      s.solution_score += stmt.solution_score;
      s.local_focus_score += stmt.local_focus_score;
      s.constructive_score += stmt.constructive_score;
      s.statements.push(stmt);

      const cats = (stmt.category || '').split(',').map((c) => c.trim()).filter(Boolean);
      cats.forEach((c) => { s.catCounts[c] = (s.catCounts[c] || 0) + 1; });
      if (stmt.meeting_date && stmt.meeting_date > s.latest_date) s.latest_date = stmt.meeting_date;
    });

    return Object.values(stats)
      .map((s) => {
        const avgEv = Number((s.evidence_score / s.count).toFixed(2));
        const avgSol = Number((s.solution_score / s.count).toFixed(2));
        const avgLoc = Number((s.local_focus_score / s.count).toFixed(2));
        const avgCon = Number((s.constructive_score / s.count).toFixed(2));
        const style = determineCouncilorStyle ? determineCouncilorStyle(avgEv, avgSol, avgLoc, avgCon) : null;
        const topCategories = Object.entries(s.catCounts).sort((a, b) => b[1] - a[1]).slice(0, 3).map((e) => e[0]);

        return {
          ...s, avg_evidence: avgEv, avg_solution: avgSol, avg_local_focus: avgLoc, avg_constructive: avgCon,
          style, topCategories, statements: s.statements.sort((a, b) => new Date(b.meeting_date) - new Date(a.meeting_date))
        };
      })
      .sort((a, b) => b.count - a.count);
  }, [statements, cityCode]);

  useEffect(() => {
    if (!initialRouteSet && speakerStats.length > 0) {
      const params = new URLSearchParams(window.location.search);
      const speakerParam = params.get('speaker');
      const compareParam = params.get('compare');

      if (compareParam) {
        const names = compareParam.split(',');
        const speakers = speakerStats.filter(s => names.includes(s.speaker));
        if (speakers.length >= 2) {
          setCompareList(speakers);
          setIsCompareMode(true);
        }
      } else if (speakerParam) {
        const speaker = speakerStats.find((s) => s.speaker === speakerParam);
        if (speaker) setSelectedSpeaker(speaker);
      }
      setTimeout(() => window.scrollTo(0, 0), 100);
      setInitialRouteSet(true);
    }
  }, [speakerStats, initialRouteSet]);

  useEffect(() => {
    const handlePopState = () => {
      const params = new URLSearchParams(window.location.search);
      const speakerParam = params.get('speaker');
      const compareParam = params.get('compare');

      if (compareParam && speakerStats.length > 0) {
        const names = compareParam.split(',');
        const speakers = speakerStats.filter(s => names.includes(s.speaker));
        setCompareList(speakers);
        setIsCompareMode(true);
        setSelectedSpeaker(null);
      } else if (speakerParam && speakerStats.length > 0) {
        const speaker = speakerStats.find((s) => s.speaker === speakerParam);
        setSelectedSpeaker(speaker || null);
        setIsCompareMode(false);
      } else {
        setSelectedSpeaker(null);
        setIsCompareMode(false);
      }
      window.scrollTo(0, 0);
    };
    window.addEventListener('popstate', handlePopState);
    return () => window.removeEventListener('popstate', handlePopState);
  }, [speakerStats]);

  const handleSpeakerClick = (speakerName) => {
    const speaker = speakerStats.find((s) => s.speaker === speakerName);
    if (speaker) {
      setSelectedSpeaker(speaker);
      setIsCompareMode(false);
      setSpeakerCategory('');
      setSpeakerSort('recent');
      const url = new URL(window.location);
      url.searchParams.set('speaker', speaker.speaker);
      url.searchParams.delete('compare');
      window.history.pushState({}, '', url);
      window.scrollTo(0, 0);
    }
  };

  const clearSpeakerAndCompare = () => {
    setSelectedSpeaker(null);
    setIsCompareMode(false);
    const url = new URL(window.location);
    url.searchParams.delete('speaker');
    url.searchParams.delete('compare');
    window.history.pushState({}, '', url);
    window.scrollTo(0, 0);
  };

  const toggleCompare = (speaker, e) => {
    if (e) e.stopPropagation();
    setCompareList(prev => {
      const exists = prev.some(s => s.speaker === speaker.speaker);
      if (exists) return prev.filter(s => s.speaker !== speaker.speaker);
      if (prev.length >= 3) {
        alert('比較できる議員は最大3名までです。');
        return prev;
      }
      return [...prev, speaker];
    });
  };

  const executeCompare = () => {
    if (compareList.length < 2) return;
    setIsCompareMode(true);
    setSelectedSpeaker(null);
    const names = compareList.map(s => s.speaker).join(',');
    const url = new URL(window.location);
    url.searchParams.set('compare', names);
    url.searchParams.delete('speaker');
    window.history.pushState({}, '', url);
    window.scrollTo(0, 0);
  };

  const filteredSpeakers = useMemo(() => {
    let targetSpeakers = new Set(speakerStats.map((s) => s.speaker));
    if (submittedQuery.trim() !== '') {
      try {
        const results = miniSearch.search(submittedQuery);
        const matchedSpeakers = new Set(results.map((r) => r.speaker));
        targetSpeakers = new Set([...targetSpeakers].filter((s) => matchedSpeakers.has(s)));
      } catch (e) { console.warn(e); }
    }
    let list = speakerStats.filter((s) => targetSpeakers.has(s.speaker));
    if (selectedCategory) list = list.filter((s) => s.topCategories.includes(selectedCategory) || s.statements.some((st) => st.category.includes(selectedCategory)));
    if (selectedCommittee) {
      if (selectedCommittee === '予算・決算特別委員会') list = list.filter((s) => s.statements.some((st) => st.meeting_title.includes('予算') || st.meeting_title.includes('決算')));
      else list = list.filter((s) => s.statements.some((st) => st.meeting_title.includes(selectedCommittee)));
    }
    if (selectedDistrict) list = list.filter((s) => s.district === selectedDistrict);

    if (sortPerspective === 'solution') list.sort((a, b) => b.avg_solution - a.avg_solution);
    else if (sortPerspective === 'local_focus') list.sort((a, b) => b.avg_local_focus - a.avg_local_focus);
    else if (sortPerspective === 'constructive') list.sort((a, b) => b.avg_constructive - a.avg_constructive);
    else if (sortPerspective === 'evidence') list.sort((a, b) => b.avg_evidence - a.avg_evidence);
    else if (sortPerspective === 'name') list.sort((a, b) => a.speaker.localeCompare(b.speaker, 'ja'));
    else if (sortPerspective === 'recent') list.sort((a, b) => new Date(b.latest_date) - new Date(a.latest_date));
    else list = shuffleWithDailySeed(list);
    return list;
  }, [speakerStats, submittedQuery, selectedCategory, selectedCommittee, selectedDistrict, sortPerspective, miniSearch]);

  const filteredThreads = useMemo(() => {
    let targetIds = new Set(statements.map((s) => s.id));
    if (submittedQuery.trim() !== '') {
      try {
        const results = miniSearch.search(submittedQuery);
        targetIds = new Set(results.map((r) => r.id));
      } catch (e) { console.warn(e); }
    }
    let list = statements.filter((s) => targetIds.has(s.id));
    if (selectedCategory) list = list.filter((s) => s.category.includes(selectedCategory));
    if (selectedCommittee) {
      if (selectedCommittee === '予算・決算特別委員会') list = list.filter((s) => s.meeting_title.includes('予算') || s.meeting_title.includes('決算'));
      else list = list.filter((s) => s.meeting_title.includes(selectedCommittee));
    }
    if (selectedDistrict) {
      list = list.filter((s) => {
        const info = getCouncilorInfo(cityCode, s.speaker);
        return info.district === selectedDistrict;
      });
    }

    if (sortPerspective === 'solution') list.sort((a, b) => b.solution_score - a.solution_score || new Date(b.meeting_date) - new Date(a.meeting_date));
    else if (sortPerspective === 'local_focus') list.sort((a, b) => b.local_focus_score - a.local_focus_score || new Date(b.meeting_date) - new Date(a.meeting_date));
    else if (sortPerspective === 'constructive') list.sort((a, b) => b.constructive_score - a.constructive_score || new Date(b.meeting_date) - new Date(a.meeting_date));
    else if (sortPerspective === 'evidence') list.sort((a, b) => b.evidence_score - a.evidence_score || new Date(b.meeting_date) - new Date(a.meeting_date));
    else if (sortPerspective === 'recent') list.sort((a, b) => new Date(b.meeting_date) - new Date(a.meeting_date));
    else list = shuffleWithDailySeed(list);

    // 💡 100件制限（.slice(0, 100)）を解除し、全件を返す
    return list;
  }, [statements, submittedQuery, selectedCategory, selectedCommittee, selectedDistrict, sortPerspective, miniSearch, cityCode]);

  const speakerFilteredThreads = useMemo(() => {
    if (!selectedSpeaker) return [];
    let list = [...selectedSpeaker.statements];
    if (speakerCategory) list = list.filter((s) => s.category.includes(speakerCategory));
    if (speakerSort === 'solution') list.sort((a, b) => b.solution_score - a.solution_score || new Date(b.meeting_date) - new Date(a.meeting_date));
    else if (speakerSort === 'local_focus') list.sort((a, b) => b.local_focus_score - a.local_focus_score || new Date(b.meeting_date) - new Date(a.meeting_date));
    else if (speakerSort === 'constructive') list.sort((a, b) => b.constructive_score - a.constructive_score || new Date(b.meeting_date) - new Date(a.meeting_date));
    else if (speakerSort === 'evidence') list.sort((a, b) => b.evidence_score - a.evidence_score || new Date(b.meeting_date) - new Date(a.meeting_date));
    else list.sort((a, b) => new Date(b.meeting_date) - new Date(a.meeting_date));
    return list;
  }, [selectedSpeaker, speakerCategory, speakerSort]);

  const timelineCache = useMemo(() => new Map(), []);

  const handleViewContext = async (stmt) => {
    setIsLoadingContext(true);
    setIsPanelOpen(true);

    try {
      const meetingId = stmt.meeting_id;
      const targetSeq = Number(stmt.sequence_number ?? stmt.speech_order ?? 0);

      let contextData = [];

      if (meetingId && targetSeq > 0) {
        let meetingTimelines = timelineCache.get(meetingId);

        if (!meetingTimelines) {
          try {
            const prefix = cityCode === 'kyoto' ? '' : `${cityCode}_`;
            const res = await fetch(`/data/${prefix}timelines/${meetingId}.json`);
            if (res.ok) {
              meetingTimelines = await res.json();
              timelineCache.set(meetingId, meetingTimelines);
            }
          } catch (fetchErr) {
            console.warn(`[handleViewContext] 会議タイムライン取得失敗 (${meetingId}):`, fetchErr);
          }
        }

        if (meetingTimelines && meetingTimelines[String(targetSeq)]) {
          contextData = meetingTimelines[String(targetSeq)];
        }
      }

      if (!contextData || contextData.length === 0) {
        contextData = [{
          ...stmt,
          is_target: true,
          statement_text: stmt.statement_text || stmt.summary || ''
        }];
      }

      setSelectedContext({
        statement: stmt,
        current: stmt,
        target: stmt,
        context: contextData,
        timeline: contextData,
        statements: contextData
      });

    } catch (err) {
      console.error('[handleViewContext] 例外:', err);
      const fallbackItem = {
        ...stmt,
        is_target: true,
        statement_text: stmt.statement_text || stmt.summary || ''
      };
      setSelectedContext({
        statement: stmt,
        current: stmt,
        context: [fallbackItem],
        timeline: [fallbackItem]
      });
    } finally {
      setIsLoadingContext(false);
    }
  };
  
  return {
    statements, isLoading,
    searchQuery, setSearchQuery,
    submittedQuery, setSubmittedQuery,
    selectedCategory, setSelectedCategory,
    selectedCommittee, setSelectedCommittee, selectedDistrict, setSelectedDistrict,
    sortPerspective, setSortPerspective, viewMode, setViewMode,
    selectedSpeaker,
    speakerCategory, setSpeakerCategory, speakerSort, setSpeakerSort, speakerFilteredThreads,
    compareList, setCompareList, isCompareMode,
    toggleCompare, executeCompare, clearSpeakerAndCompare, handleSpeakerClick, handleViewContext,
    selectedContext, isPanelOpen, setIsPanelOpen, isLoadingContext,
    topicStats, speakerStats, filteredSpeakers, filteredThreads
  };
}