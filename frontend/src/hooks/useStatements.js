import { useState, useEffect, useMemo } from 'react';
import { createClient } from '@supabase/supabase-js';
import MiniSearch from 'minisearch';
import { VALID_COUNCILORS, cleanName, determineCouncilorStyle } from '../utils/styleHelpers';
import { getCouncilorMasterInfo } from '../utils/councilorMaster';

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL || '';
const supabaseKey = import.meta.env.VITE_SUPABASE_ANON_KEY || '';
const supabase = createClient(supabaseUrl, supabaseKey);

export function useStatements() {
  const [statements, setStatements] = useState([]);
  const [isLoading, setIsLoading] = useState(true);

  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('');
  const [selectedCommittee, setSelectedCommittee] = useState('');
  const [selectedDistrict, setSelectedDistrict] = useState('');
  const [sortPerspective, setSortPerspective] = useState('recent');
  const [viewMode, setViewMode] = useState('speakers');

  const [selectedSpeaker, setSelectedSpeaker] = useState(null);
  const [speakerCategory, setSpeakerCategory] = useState('');
  const [speakerSort, setSpeakerSort] = useState('recent');

  const [selectedContext, setSelectedContext] = useState(null);
  const [isPanelOpen, setIsPanelOpen] = useState(false);
  const [isLoadingContext, setIsLoadingContext] = useState(false);

  // 💡 比較機能用ステートとルーティングフラグ
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
    fetchStatements();
  }, []);

  const fetchStatements = async () => {
    setIsLoading(true);
    let allRecords = [];
    try {
      const res = await fetch('/data/statements_summary.json');
      if (res.ok) allRecords = await res.json();
    } catch {
      console.warn("Static JSON fetch failed, falling back to Supabase.");
    }

    if (!allRecords || allRecords.length === 0) {
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
      } catch (err) { console.error(err); }
    }

    const validData = [];
    allRecords.forEach((stmt, idx) => {
      const speakerName = cleanName(stmt.speaker);
      if (!VALID_COUNCILORS.includes(speakerName)) return;

      const ev = Number(stmt.evidence_score || 0);
      const sol = Number(stmt.solution_score || 0);
      const lf = Number(stmt.local_focus_score || 0);
      const cons = Number(stmt.constructive_score || 0);
      const cat = stmt.category ? String(stmt.category).replace(/[\[\]'"]/g, '') : "政策質疑";

      if (cat.includes("進行") || (ev === 0 && sol === 0 && lf === 0 && cons === 0)) return;

      validData.push({
        ...stmt, id: stmt.id || `local_${idx}`, category: cat,
        evidence_score: ev, solution_score: sol, local_focus_score: lf, constructive_score: cons
      });
    });
    miniSearch.removeAll();
    miniSearch.addAll(validData);
    setStatements(validData);
    setIsLoading(false);
  };

  const topicStats = useMemo(() => {
    if (statements.length === 0) return [];
    const counts = {};
    statements.forEach((s) => {
      const cats = s.category.split(',').map((c) => c.trim()).filter(Boolean);
      cats.forEach((c) => { counts[c] = (counts[c] || 0) + 1; });
    });
    const total = Object.values(counts).reduce((a, b) => a + b, 0);
    return Object.entries(counts)
      .map(([name, count]) => ({ name, count, percentage: ((count / total) * 100).toFixed(1) }))
      .sort((a, b) => b.count - a.count)
      .slice(0, 8);
  }, [statements]);

  const speakerStats = useMemo(() => {
    const stats = {};
    statements.forEach((stmt) => {
      const spk = stmt.speaker;
      if (!stats[spk]) {
        const masterInfo = getCouncilorMasterInfo(spk);
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

      const cats = stmt.category.split(',').map((c) => c.trim()).filter(Boolean);
      cats.forEach((c) => { s.catCounts[c] = (s.catCounts[c] || 0) + 1; });
      if (stmt.meeting_date && stmt.meeting_date > s.latest_date) s.latest_date = stmt.meeting_date;
    });

    return Object.values(stats)
      .map((s) => {
        const avgEv = Number((s.evidence_score / s.count).toFixed(2));
        const avgSol = Number((s.solution_score / s.count).toFixed(2));
        const avgLoc = Number((s.local_focus_score / s.count).toFixed(2));
        const avgCon = Number((s.constructive_score / s.count).toFixed(2));
        const style = determineCouncilorStyle(avgEv, avgSol, avgLoc, avgCon);
        const topCategories = Object.entries(s.catCounts).sort((a, b) => b[1] - a[1]).slice(0, 3).map((e) => e[0]);

        return {
          ...s, avg_evidence: avgEv, avg_solution: avgSol, avg_local_focus: avgLoc, avg_constructive: avgCon,
          style, topCategories, statements: s.statements.sort((a, b) => new Date(b.meeting_date) - new Date(a.meeting_date))
        };
      })
      .sort((a, b) => b.count - a.count);
  }, [statements]);

  // 💡 URLルーティングの初期化
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

  // 💡 ブラウザ「戻る/進む」への対応
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

  // 💡 SPA画面遷移とURL更新アクション
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
    if (searchQuery.trim() !== '') {
      const results = miniSearch.search(searchQuery);
      const matchedSpeakers = new Set(results.map((r) => r.speaker));
      targetSpeakers = new Set([...targetSpeakers].filter((s) => matchedSpeakers.has(s)));
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
    else list.sort((a, b) => new Date(b.latest_date) - new Date(a.latest_date));
    return list;
  }, [speakerStats, searchQuery, selectedCategory, selectedCommittee, selectedDistrict, sortPerspective, miniSearch]);

  const filteredThreads = useMemo(() => {
    let targetIds = new Set(statements.map((s) => s.id));
    if (searchQuery.trim() !== '') {
      const results = miniSearch.search(searchQuery);
      targetIds = new Set(results.map((r) => r.id));
    }
    let list = statements.filter((s) => targetIds.has(s.id));
    if (selectedCategory) list = list.filter((s) => s.category.includes(selectedCategory));
    if (selectedCommittee) {
      if (selectedCommittee === '予算・決算特別委員会') list = list.filter((s) => s.meeting_title.includes('予算') || s.meeting_title.includes('決算'));
      else list = list.filter((s) => s.meeting_title.includes(selectedCommittee));
    }
    if (selectedDistrict) {
      list = list.filter((s) => {
        const info = getCouncilorMasterInfo(s.speaker);
        return info.district === selectedDistrict;
      });
    }
    if (sortPerspective === 'solution') list.sort((a, b) => b.solution_score - a.solution_score || new Date(b.meeting_date) - new Date(a.meeting_date));
    else if (sortPerspective === 'local_focus') list.sort((a, b) => b.local_focus_score - a.local_focus_score || new Date(b.meeting_date) - new Date(a.meeting_date));
    else if (sortPerspective === 'constructive') list.sort((a, b) => b.constructive_score - a.constructive_score || new Date(b.meeting_date) - new Date(a.meeting_date));
    else if (sortPerspective === 'evidence') list.sort((a, b) => b.evidence_score - a.evidence_score || new Date(b.meeting_date) - new Date(a.meeting_date));
    else list.sort((a, b) => new Date(b.meeting_date) - new Date(a.meeting_date));

    return list.slice(0, 100);
  }, [statements, searchQuery, selectedCategory, selectedCommittee, selectedDistrict, sortPerspective, miniSearch]);

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

  const handleViewContext = async (stmt) => {
    setIsPanelOpen(true);
    setIsLoadingContext(true);
    setSelectedContext({ statement: stmt, context: [] });
    const startSeq = Math.max(1, stmt.sequence_number - 15);
    const endSeq = stmt.sequence_number + 15;
    try {
      const { data, error } = await supabase
        .from('statements')
        .select('*')
        .eq('meeting_id', stmt.meeting_id)
        .gte('sequence_number', startSeq)
        .lte('sequence_number', endSeq)
        .order('sequence_number', { ascending: true });
      if (error) throw error;
      const formatted = data.map((item) => ({
        ...item,
        is_target: item.sequence_number === stmt.sequence_number,
        is_admin: !VALID_COUNCILORS.includes(cleanName(item.speaker)),
        is_short_procedural:
          (item.statement_text || '').trim().length < 35 &&
          (item.statement_text.includes('異議なし') || item.statement_text.endsWith('委員。'))
      }));
      setSelectedContext({ statement: stmt, context: formatted });
    } catch (err) { console.error(err); } finally { setIsLoadingContext(false); }
  };

  return {
    statements, isLoading,
    searchQuery, setSearchQuery, selectedCategory, setSelectedCategory,
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