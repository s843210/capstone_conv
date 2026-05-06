import React, {useMemo, useState} from 'react';
import {SafeAreaView, Text, TextInput, Pressable, FlatList, View, Alert} from 'react-native';
import {ProductListScreenProps} from '../types';
import {styles} from '../styles/commonStyles';
import {PRODUCTS} from '../data/products';

type Props = ProductListScreenProps & {
  currentUser: string;
  logoutUser: () => Promise<boolean>;
};

export default function ProductListScreen({navigation, currentUser, logoutUser}: Props) {
  const [keyword, setKeyword] = useState('');
  const [category, setCategory] = useState('전체');
  const hasKeyword = keyword.trim().length > 0;

  const categories = ['전체', ...new Set(PRODUCTS.map(p => p.category))];

  const filtered = useMemo(() => {
    return PRODUCTS.filter(p => {
      const categoryOk = category === '전체' || p.category === category;
      const keywordOk = p.name.includes(keyword) || p.description.includes(keyword);
      return categoryOk && keywordOk;
    });
  }, [keyword, category]);

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

      <View style={styles.rowWrap}>
        {categories.map(c => (
          <Pressable
            key={c}
            style={[styles.chip, c === category && styles.chipActive]}
            onPress={() => setCategory(c)}>
            <Text style={[styles.chipText, c === category && styles.chipTextActive]}>{c}</Text>
          </Pressable>
        ))}
      </View>
      <Text style={styles.resultCountText}>검색 결과 {filtered.length}개</Text>

      <FlatList
        data={filtered}
        keyExtractor={item => item.id}
        renderItem={({item}) => (
          <Pressable
            style={[styles.card, item.stock <= 0 && styles.cardDisabled]}
            onPress={() => navigation.navigate('ProductDetail', {product: item})}>
            <Text style={styles.cardTitle}>{item.name}</Text>
            <View style={styles.statusRow}>
              <Text style={styles.cardMeta}>카테고리: {item.category}</Text>
              <Text style={item.stock > 0 ? styles.statusText : styles.soldOutText}>
                {item.stock > 0 ? '요청 가능' : '품절'}
              </Text>
            </View>
            <Text style={styles.cardMeta}>
              재고 상태: {item.stock > 0 ? `${item.stock}개 남음` : '재고 없음'}
            </Text>
          </Pressable>
        )}
        ListEmptyComponent={
          <Text style={styles.emptyText}>
            {PRODUCTS.length === 0
              ? '등록된 상품이 없습니다.'
              : '조건에 맞는 상품이 없습니다. 검색어를 다시 확인해 주세요.'}
          </Text>
        }
      />

      <Pressable style={styles.secondaryBtn} onPress={() => navigation.navigate('MyRequests')}>
        <Text style={styles.secondaryBtnText}>내 요청 목록 보기</Text>
      </Pressable>
    </SafeAreaView>
  );
}
