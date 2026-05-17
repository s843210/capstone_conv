import React, {useCallback, useEffect, useMemo, useState} from 'react';
import {
  SafeAreaView,
  Text,
  TextInput,
  Pressable,
  FlatList,
  View,
  Alert,
  ScrollView,
  StyleSheet,
} from 'react-native';
import {Product, ProductListScreenProps} from '../types';
import {fetchStudentProducts} from '../api/studentApi';

type Props = ProductListScreenProps & {
  currentUser: string;
  logoutUser: () => Promise<boolean>;
};

type StockState = 'available' | 'low' | 'soldout';

const categoryIconMap: Record<string, string> = {
  음료: '🥤',
  과자: '🍪',
  음식: '🍚',
  문구: '✏️',
  생활용품: '🧻',
  기타: '📦',
};

const getCategoryIcon = (rawCategory: string): string => {
  const category = rawCategory.trim();
  if (categoryIconMap[category]) {
    return categoryIconMap[category];
  }

  if (category.includes('음료')) return '🥤';
  if (category.includes('과자')) return '🍪';
  if (category.includes('음식')) return '🍚';
  if (category.includes('문구')) return '✏️';
  if (category.includes('생활')) return '🧻';

  return '📦';
};

const getStockState = (stock?: number): StockState => {
  if (typeof stock !== 'number') {
    return 'available';
  }
  if (stock <= 0) {
    return 'soldout';
  }
  if (stock <= 5) {
    return 'low';
  }
  return 'available';
};

const stockBadgeText: Record<StockState, string> = {
  available: '요청 가능',
  low: '재고 부족',
  soldout: '품절',
};

export default function ProductListScreen({navigation, currentUser, logoutUser}: Props) {
  const [products, setProducts] = useState<Product[]>([]);
  const [loading, setLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState('');
  const [keyword, setKeyword] = useState('');
  const [category, setCategory] = useState('전체');
  const [categoryExpanded, setCategoryExpanded] = useState(false);
  const hasKeyword = keyword.trim().length > 0;

  // 상품 목록 API를 호출해 화면 상태를 갱신(실패 시 기존 목록 유지)
  const loadProducts = useCallback(async () => {
    setLoading(true);
    setErrorMessage('');

    try {
      const data = await fetchStudentProducts();
      setProducts(data);
    } catch (error) {
      const message = error instanceof Error ? error.message : '상품 목록 조회 실패';
      setErrorMessage(message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadProducts();
  }, [loadProducts]);

  const categories = useMemo(() => ['전체', ...new Set(products.map(p => p.category))], [products]);
  const visibleCategories = useMemo(() => {
    if (categoryExpanded || categories.length <= 6) {
      return categories;
    }

    const collapsed = categories.slice(0, 5);
    if (collapsed.includes(category)) {
      return collapsed;
    }

    return [...collapsed.slice(0, 4), category];
  }, [categories, category, categoryExpanded]);
  const canToggleCategories = categories.length > 6;

  const filtered = useMemo(() => {
    return products.filter(p => {
      const categoryOk = category === '전체' || p.category === category;
      const keywordOk = p.name.includes(keyword) || p.category.includes(keyword);
      return categoryOk && keywordOk;
    });
  }, [products, keyword, category]);

  const handleLogout = () => {
    Alert.alert('로그아웃', '로그아웃하시겠습니까?', [
      {text: '취소', style: 'cancel'},
      {
        text: '로그아웃',
        style: 'destructive',
        onPress: async () => {
          const loggedOut = await logoutUser();
          if (!loggedOut) {
            Alert.alert('로그아웃 오류', '로그아웃 중 오류가 발생했습니다.');
            return;
          }

          navigation.reset({index: 0, routes: [{name: 'Login'}]});
        },
      },
    ]);
  };

  const selectCategory = (selectedCategory: string) => {
    setCategory(selectedCategory);
    setCategoryExpanded(false);
  };

  return (
    <SafeAreaView style={localStyles.page}>
      <View style={localStyles.headerRow}>
        <Text style={localStyles.title}>상품 목록</Text>
        <Pressable style={localStyles.logoutBtn} onPress={handleLogout}>
          <Text style={localStyles.logoutBtnText}>로그아웃</Text>
        </Pressable>
      </View>

      <View style={localStyles.contentArea}>
        <View style={localStyles.searchRow}>
          <TextInput
            placeholder="상품명 검색"
            placeholderTextColor="#94A3B8"
            value={keyword}
            onChangeText={setKeyword}
            style={localStyles.searchInput}
          />
          {hasKeyword && (
            <Pressable style={localStyles.clearBtn} onPress={() => setKeyword('')}>
              <Text style={localStyles.clearBtnText}>초기화</Text>
            </Pressable>
          )}
        </View>

        {categoryExpanded ? (
          <View style={localStyles.categoryExpandedBox}>
            <ScrollView
              nestedScrollEnabled
              bounces={false}
              alwaysBounceVertical={false}
              overScrollMode="never"
              showsVerticalScrollIndicator
              style={localStyles.categoryExpandedList}
              contentContainerStyle={localStyles.categoryExpandedContent}
              scrollEventThrottle={16}>
              {visibleCategories.map(c => (
                <Pressable
                  key={c}
                  style={[localStyles.chip, c === category && localStyles.chipActive]}
                  onPress={() => selectCategory(c)}>
                  <Text style={[localStyles.chipText, c === category && localStyles.chipTextActive]}>{c}</Text>
                </Pressable>
              ))}
            </ScrollView>
            <View style={localStyles.categoryExpandedFooter}>
              {canToggleCategories && (
                <Pressable style={localStyles.categoryMoreBtn} onPress={() => setCategoryExpanded(false)}>
                  <Text style={localStyles.categoryMoreBtnText}>접기</Text>
                </Pressable>
              )}
            </View>
          </View>
        ) : (
          <View style={localStyles.categoryCollapsedRow}>
            <ScrollView
              horizontal
              showsHorizontalScrollIndicator={false}
              style={localStyles.categoryScroll}
              contentContainerStyle={localStyles.categoryScrollContent}>
              {visibleCategories.map(c => (
                <Pressable
                  key={c}
                  style={[localStyles.chip, c === category && localStyles.chipActive]}
                  onPress={() => selectCategory(c)}>
                  <Text style={[localStyles.chipText, c === category && localStyles.chipTextActive]}>{c}</Text>
                </Pressable>
              ))}
            </ScrollView>
            {canToggleCategories && (
              <Pressable style={localStyles.categoryMoreBtn} onPress={() => setCategoryExpanded(true)}>
                <Text style={localStyles.categoryMoreBtnText}>더보기</Text>
              </Pressable>
            )}
          </View>
        )}

        <Text style={localStyles.resultCountText}>검색 결과 {filtered.length}개</Text>

        {loading && <Text style={localStyles.emptyText}>상품 목록을 불러오는 중입니다...</Text>}

        {!loading && !!errorMessage && (
          <View style={localStyles.productCard}>
            <Text style={localStyles.emptyText}>{errorMessage}</Text>
            <Pressable style={localStyles.primaryBtn} onPress={loadProducts}>
              <Text style={localStyles.primaryBtnText}>다시 시도</Text>
            </Pressable>
          </View>
        )}

        {!loading && (
          <FlatList
            data={filtered}
            keyExtractor={item => item.pluCode}
            renderItem={({item}) => {
              const icon = getCategoryIcon(item.category);
              const stockState = getStockState(item.stock);

              return (
                <Pressable
                  style={localStyles.productCard}
                  onPress={() => navigation.navigate('ProductDetail', {product: item})}>
                  <View style={localStyles.productRow}>
                    <View style={localStyles.categoryIconWrap}>
                      <Text style={localStyles.categoryIcon}>{icon}</Text>
                    </View>

                    <View style={localStyles.productInfoWrap}>
                      <Text style={localStyles.productName}>{item.name}</Text>
                      <Text style={localStyles.productMeta}>
                        {item.category} {'\u00B7'} 재고 {typeof item.stock === 'number' ? item.stock : '-'}개
                      </Text>
                    </View>

                    <View
                      style={[
                        localStyles.stockBadge,
                        stockState === 'available'
                          ? localStyles.stockBadge_available
                          : stockState === 'low'
                            ? localStyles.stockBadge_low
                            : localStyles.stockBadge_soldout,
                      ]}>
                      <Text
                        style={[
                          localStyles.stockBadgeText,
                          stockState === 'available'
                            ? localStyles.stockBadgeText_available
                            : stockState === 'low'
                              ? localStyles.stockBadgeText_low
                              : localStyles.stockBadgeText_soldout,
                        ]}>
                        {stockBadgeText[stockState]}
                      </Text>
                    </View>
                  </View>
                </Pressable>
              );
            }}
            ListEmptyComponent={
              <View style={localStyles.emptyWrap}>
                <Text style={localStyles.emptyIcon}>🔍</Text>
                <Text style={localStyles.emptyTitle}>검색 결과가 없어요</Text>
                <Text style={localStyles.emptySubText}>다른 상품명으로 검색해보세요.</Text>
              </View>
            }
            contentContainerStyle={localStyles.listContent}
          />
        )}

        <View style={localStyles.bottomActionRow}>
          <Pressable style={localStyles.secondaryBtnPrimary} onPress={() => navigation.navigate('Suggestions')}>
            <Text style={localStyles.secondaryBtnPrimaryText}>건의사항 보기</Text>
          </Pressable>
          <Pressable style={localStyles.secondaryBtnPrimary} onPress={() => navigation.navigate('MyRequests')}>
            <Text style={localStyles.secondaryBtnPrimaryText}>내 요청 목록</Text>
          </Pressable>
        </View>
      </View>
    </SafeAreaView>
  );
}

const localStyles = StyleSheet.create({
  page: {
    flex: 1,
    backgroundColor: '#F8FAFC',
  },
  headerRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: 16,
    paddingTop: 10,
    paddingBottom: 10,
  },
  title: {
    color: '#111827',
    fontSize: 24,
    fontWeight: '800',
  },
  logoutBtn: {
    borderWidth: 1,
    borderColor: '#CBD5E1',
    borderRadius: 10,
    backgroundColor: '#FFFFFF',
    paddingHorizontal: 10,
    paddingVertical: 7,
  },
  logoutBtnText: {
    color: '#475569',
    fontWeight: '700',
    fontSize: 13,
  },
  contentArea: {
    flex: 1,
    paddingHorizontal: 16,
    paddingTop: 8,
  },
  searchRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    marginBottom: 12,
  },
  searchInput: {
    flex: 1,
    backgroundColor: '#FFFFFF',
    borderRadius: 12,
    borderWidth: 1,
    borderColor: '#E5E7EB',
    paddingHorizontal: 14,
    paddingVertical: 12,
    color: '#111827',
    fontSize: 15,
  },
  clearBtn: {
    borderWidth: 1,
    borderColor: '#CBD5E1',
    borderRadius: 10,
    backgroundColor: '#FFFFFF',
    paddingHorizontal: 12,
    paddingVertical: 10,
  },
  clearBtnText: {
    color: '#475569',
    fontWeight: '700',
    fontSize: 13,
  },
  categoryExpandedBox: {
    marginBottom: 10,
  },
  categoryExpandedList: {
    maxHeight: 170,
  },
  categoryExpandedContent: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 8,
    paddingBottom: 8,
  },
  categoryExpandedFooter: {
    flexDirection: 'row',
    justifyContent: 'flex-end',
    alignItems: 'center',
    gap: 8,
  },
  categoryCollapsedRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    marginBottom: 10,
  },
  categoryScroll: {
    flex: 1,
  },
  categoryScrollContent: {
    flexDirection: 'row',
    gap: 8,
    paddingRight: 2,
  },
  chip: {
    borderRadius: 999,
    borderWidth: 1,
    borderColor: '#CBD5E1',
    paddingHorizontal: 12,
    paddingVertical: 8,
    backgroundColor: '#FFFFFF',
  },
  chipActive: {
    backgroundColor: '#0060AF',
    borderColor: '#0060AF',
  },
  chipText: {
    color: '#334155',
    fontSize: 13,
    fontWeight: '600',
  },
  chipTextActive: {
    color: '#FFFFFF',
  },
  categoryMoreBtn: {
    borderRadius: 999,
    borderWidth: 1,
    borderColor: '#0060AF',
    backgroundColor: '#EAF2FF',
    paddingHorizontal: 12,
    paddingVertical: 8,
  },
  categoryMoreBtnText: {
    color: '#0060AF',
    fontWeight: '700',
    fontSize: 13,
  },
  resultCountText: {
    color: '#334155',
    fontSize: 14,
    fontWeight: '600',
    marginBottom: 10,
  },
  listContent: {
    paddingBottom: 18,
  },
  productCard: {
    backgroundColor: '#FFFFFF',
    borderRadius: 14,
    padding: 14,
    marginBottom: 12,
    borderWidth: 1,
    borderColor: '#E5E7EB',
    shadowColor: '#0F172A',
    shadowOpacity: 0.05,
    shadowRadius: 8,
    shadowOffset: {width: 0, height: 4},
    elevation: 1,
  },
  productRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
  },
  categoryIconWrap: {
    width: 42,
    height: 42,
    borderRadius: 999,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: 'rgba(0,96,175,0.1)',
  },
  categoryIcon: {
    fontSize: 20,
  },
  productInfoWrap: {
    flex: 1,
  },
  productName: {
    color: '#111827',
    fontSize: 16,
    fontWeight: '700',
    marginBottom: 3,
  },
  productMeta: {
    color: '#64748B',
    fontSize: 13,
  },
  stockBadge: {
    borderRadius: 999,
    paddingHorizontal: 10,
    paddingVertical: 6,
  },
  stockBadge_available: {
    backgroundColor: '#DCFCE7',
  },
  stockBadge_low: {
    backgroundColor: '#FEF3C7',
  },
  stockBadge_soldout: {
    backgroundColor: '#E5E7EB',
  },
  stockBadgeText: {
    fontSize: 12,
    fontWeight: '700',
  },
  stockBadgeText_available: {
    color: '#166534',
  },
  stockBadgeText_low: {
    color: '#92400E',
  },
  stockBadgeText_soldout: {
    color: '#475569',
  },
  emptyWrap: {
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 46,
  },
  emptyIcon: {
    fontSize: 28,
    marginBottom: 6,
  },
  emptyTitle: {
    color: '#334155',
    fontSize: 16,
    fontWeight: '700',
    marginBottom: 4,
  },
  emptySubText: {
    color: '#64748B',
    fontSize: 14,
  },
  emptyText: {
    textAlign: 'center',
    marginTop: 24,
    color: '#6B7280',
    fontSize: 15,
    lineHeight: 22,
  },
  primaryBtn: {
    backgroundColor: '#0060AF',
    paddingVertical: 13,
    borderRadius: 12,
    alignItems: 'center',
    marginTop: 12,
  },
  primaryBtnText: {
    color: '#FFFFFF',
    fontWeight: '700',
    fontSize: 15,
  },
  bottomActionRow: {
    paddingBottom: 8,
    gap: 8,
  },
  secondaryBtn: {
    borderWidth: 1,
    borderColor: '#0060AF',
    backgroundColor: '#EAF2FF',
    paddingVertical: 12,
    borderRadius: 12,
    alignItems: 'center',
  },
  secondaryBtnText: {
    color: '#0060AF',
    fontWeight: '700',
    fontSize: 14,
  },
  secondaryBtnPrimary: {
    borderWidth: 1,
    borderColor: '#0060AF',
    backgroundColor: '#0060AF',
    paddingVertical: 12,
    borderRadius: 12,
    alignItems: 'center',
  },
  secondaryBtnPrimaryText: {
    color: '#FFFFFF',
    fontWeight: '700',
    fontSize: 14,
  },
});


