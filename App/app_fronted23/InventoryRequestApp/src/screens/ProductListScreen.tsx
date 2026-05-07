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
} from 'react-native';
import {Product, ProductListScreenProps} from '../types';
import {styles} from '../styles/commonStyles';
import {fetchStudentProducts} from '../api/studentApi';

type Props = ProductListScreenProps & {
  currentUser: string;
  logoutUser: () => Promise<boolean>;
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
    <SafeAreaView style={styles.page}>
      <View style={styles.headerRow}>
        <Text style={styles.title}>상품 목록</Text>
        <Pressable style={styles.logoutBtn} onPress={handleLogout}>
          <Text style={styles.logoutBtnText}>로그아웃</Text>
        </Pressable>
      </View>
      <Text style={styles.subtitle}>{currentUser}님, 필요한 상품을 요청해보세요.</Text>

      <View style={styles.searchRow}>
        <TextInput
          placeholder="상품명 검색"
          value={keyword}
          onChangeText={setKeyword}
          style={[styles.input, styles.searchInput]}
        />
        {hasKeyword && (
          <Pressable style={styles.clearBtn} onPress={() => setKeyword('')}>
            <Text style={styles.clearBtnText}>초기화</Text>
          </Pressable>
        )}
      </View>

      {categoryExpanded ? (
        <View style={styles.categoryExpandedBox}>
          <ScrollView
            nestedScrollEnabled
            bounces={false}
            alwaysBounceVertical={false}
            overScrollMode="never"
            showsVerticalScrollIndicator
            style={styles.categoryExpandedList}
            contentContainerStyle={styles.categoryExpandedContent}
            scrollEventThrottle={16}>
            {visibleCategories.map(c => (
              <Pressable
                key={c}
                style={[styles.chip, c === category && styles.chipActive]}
                onPress={() => selectCategory(c)}>
                <Text style={[styles.chipText, c === category && styles.chipTextActive]}>{c}</Text>
              </Pressable>
            ))}
          </ScrollView>
          <View style={styles.categoryExpandedFooter}>
            {canToggleCategories && (
              <Pressable style={styles.categoryMoreBtn} onPress={() => setCategoryExpanded(false)}>
                <Text style={styles.categoryMoreBtnText}>접기</Text>
              </Pressable>
            )}
          </View>
        </View>
      ) : (
        <View style={styles.categoryCollapsedRow}>
          <ScrollView
            horizontal
            showsHorizontalScrollIndicator={false}
            style={styles.categoryScroll}
            contentContainerStyle={styles.categoryScrollContent}>
            {visibleCategories.map(c => (
              <Pressable
                key={c}
                style={[styles.chip, c === category && styles.chipActive]}
                onPress={() => selectCategory(c)}>
                <Text style={[styles.chipText, c === category && styles.chipTextActive]}>{c}</Text>
              </Pressable>
            ))}
          </ScrollView>
          {canToggleCategories && (
            <Pressable style={styles.categoryMoreBtn} onPress={() => setCategoryExpanded(true)}>
              <Text style={styles.categoryMoreBtnText}>더보기</Text>
            </Pressable>
          )}
        </View>
      )}
      <Text style={styles.resultCountText}>검색 결과 {filtered.length}개</Text>

      {loading && <Text style={styles.emptyText}>상품 목록을 불러오는 중입니다...</Text>}

      {!loading && !!errorMessage && (
        <View style={styles.card}>
          <Text style={styles.emptyText}>{errorMessage}</Text>
          <Pressable style={styles.primaryBtn} onPress={loadProducts}>
            <Text style={styles.primaryBtnText}>다시 시도</Text>
          </Pressable>
        </View>
      )}

      {!loading && (
        <FlatList
          data={filtered}
          keyExtractor={item => item.pluCode}
          renderItem={({item}) => (
            <Pressable
              style={styles.card}
              onPress={() => navigation.navigate('ProductDetail', {product: item})}>
              <Text style={styles.cardTitle}>{item.name}</Text>
              <View style={styles.statusRow}>
                <Text style={styles.cardMeta}>카테고리: {item.category}</Text>
                <Text style={styles.statusText}>신청 가능</Text>
              </View>
            </Pressable>
          )}
          ListEmptyComponent={
            <Text style={styles.emptyText}>
              {products.length === 0
                ? '등록된 상품이 없습니다.'
                : '조건에 맞는 상품이 없습니다. 검색어를 다시 확인해 주세요.'}
            </Text>
          }
        />
      )}

      <Pressable style={styles.secondaryBtn} onPress={() => navigation.navigate('MyRequests')}>
        <Text style={styles.secondaryBtnText}>내 요청 목록 보기</Text>
      </Pressable>
    </SafeAreaView>
  );
}
