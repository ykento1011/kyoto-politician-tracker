import React, { useRef, useEffect } from 'react';
import { Landmark } from 'lucide-react';

const CITIES = [
  { code: 'kyoto', name: '京都市', shortName: '京都', path: '/kyoto/' },
  { code: 'osaka', name: '大阪市', shortName: '大阪', path: '/osaka/' },
  { code: 'nagoya', name: '名古屋市', shortName: '名古屋', path: '/nagoya/' },
  { code: 'yokohama', name: '横浜市', shortName: '横浜', path: '/yokohama/' },
  { code: 'kobe', name: '神戸市', shortName: '神戸', path: '/kobe/' },
];

export default function CitySelector({ currentCity = 'kyoto', onSelectCity }) {
  const activeTabRef = useRef(null);

  // アクティブな都市タブが見えるように中央へ自動スクロール
  useEffect(() => {
    if (activeTabRef.current) {
      activeTabRef.current.scrollIntoView({
        behavior: 'smooth',
        block: 'nearest',
        inline: 'center',
      });
    }
  }, [currentCity]);

  const handleCityClick = (cityCode) => {
    if (onSelectCity) {
      onSelectCity(cityCode);
    } else {
      if (cityCode === 'portal') {
        window.location.href = '/';
        return;
      }
      if (cityCode === currentCity) return;
      window.location.href = `/${cityCode}/`;
    }
  };

  return (
    <nav
      aria-label="自治体切り替え"
      className="flex items-center gap-1.5 overflow-x-auto no-scrollbar snap-x py-1 px-1 -mx-1"
    >
      <button
        type="button"
        onClick={() => handleCityClick('portal')}
        className={`snap-start shrink-0 min-h-[44px] px-3.5 py-2 rounded-xl text-xs font-black transition-all flex items-center gap-1.5 border cursor-pointer ${
          !currentCity
            ? 'bg-indigo-600 text-white border-indigo-600 shadow-xs'
            : 'border-slate-200 bg-white text-slate-600 hover:bg-slate-50 active:bg-slate-100 shadow-2xs'
        }`}
        title="全国5都市総合ポータルへ"
      >
        <Landmark className="w-3.5 h-3.5 text-indigo-600 shrink-0" />
        <span>ポータル</span>
      </button>

      {CITIES.map((city) => {
        const isActive = city.code === currentCity;
        return (
          <button
            key={city.code}
            ref={isActive ? activeTabRef : null}
            type="button"
            onClick={() => handleCityClick(city.code)}
            className={`snap-center shrink-0 min-h-[44px] min-w-[76px] px-4 py-2 rounded-xl text-xs font-bold transition-all flex items-center justify-center cursor-pointer border ${
              isActive
                ? 'bg-indigo-600 text-white border-indigo-600 shadow-xs font-black'
                : 'bg-white text-slate-700 border-slate-200 hover:bg-slate-50 active:bg-slate-100'
            }`}
          >
            <span>{city.name}</span>
            {isActive && (
              <span className="w-1.5 h-1.5 rounded-full bg-white ml-1.5 animate-pulse" />
            )}
          </button>
        );
      })}
    </nav>
  );
}
