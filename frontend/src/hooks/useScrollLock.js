import { useEffect, useRef } from 'react';

/**
 * iOS Safari / Android Chrome での画面トップ戻り（y=0リセット）を防ぐスクロールロックフック
 * @param {boolean} lock ロック状態
 */
export function useScrollLock(lock = false) {
  const scrollPosRef = useRef(0);

  useEffect(() => {
    if (!lock) return;

    // 現在のスクロール位置を退避
    const scrollY = window.scrollY || window.pageYOffset || document.documentElement.scrollTop || 0;
    scrollPosRef.current = scrollY;

    // 既存の body スタイルを退避
    const originalStyle = {
      position: document.body.style.position,
      top: document.body.style.top,
      left: document.body.style.left,
      right: document.body.style.right,
      width: document.body.style.width,
      overflow: document.body.style.overflow,
    };

    // body を fixed で固定し、ページトップへの強制スクロールを物理的に遮断
    document.body.style.position = 'fixed';
    document.body.style.top = `-${scrollY}px`;
    document.body.style.left = '0';
    document.body.style.right = '0';
    document.body.style.width = '100%';
    document.body.style.overflow = 'hidden';

    return () => {
      // スタイルを原状復帰
      document.body.style.position = originalStyle.position;
      document.body.style.top = originalStyle.top;
      document.body.style.left = originalStyle.left;
      document.body.style.right = originalStyle.right;
      document.body.style.width = originalStyle.width;
      document.body.style.overflow = originalStyle.overflow;

      // 退避していたスクロール位置へ即時復元
      window.scrollTo(0, scrollPosRef.current);
    };
  }, [lock]);
}

export default useScrollLock;
