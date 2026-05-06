import React, {useEffect, useMemo, useState} from 'react';
import {
  SafeAreaView,
  View,
  Text,
  TextInput,
  Pressable,
  FlatList,
  StyleSheet,
  Alert,
} from 'react-native';
import {NavigationContainer} from '@react-navigation/native';
import {createNativeStackNavigator} from '@react-navigation/native-stack';
import AsyncStorage from '@react-native-async-storage/async-storage';

type Product = {
  id: string;
  name: string;
  category: string;
  stock: number;
  description: string;
};

type RequestItem = {
  id: string;
  productId: string;
  productName: string;
  qty: number;
  createdAt: string;
};

type RootStackParamList = {
  Start: undefined;
  Login: undefined;
  ProductList: undefined;
  ProductDetail: {product: Product};
  RequestQty: {product: Product};
  RequestDone: {item: RequestItem};
  MyRequests: undefined;
};

const Stack = createNativeStackNavigator<RootStackParamList>();
const REQUESTS_STORAGE_KEY = 'my_requests_v1';

const PRODUCTS: Product[] = [
  {
    id: 'p1',
    name: '삼각김밥',
    category: '간편식',
    stock: 12,
    description: '참치마요 삼각김밥',
  },
  {
    id: 'p2',
    name: '컵라면',
    category: '라면',
    stock: 20,
    description: '매운맛 컵라면',
  },
  {
    id: 'p3',
    name: '생수',
    category: '음료',
    stock: 35,
    description: '500ml 생수',
  },
  {
    id: 'p4',
    name: '아이스커피',
    category: '음료',
    stock: 8,
    description: '편의점 아이스커피',
  },
  {
    id: 'p5',
    name: '초콜릿',
    category: '과자',
    stock: 15,
    description: '간식용 초콜릿',
  },
  {
    id: 'p6',
    name: '물티슈',
    category: '생활용품',
    stock: 0,
    description: '휴대용 물티슈',
  },
];

function StartScreen({navigation}: any) {
  return (
    <SafeAreaView style={styles.page}>
      <View style={styles.heroCard}>
        <Text style={styles.badge}>교내 편의점</Text>
        <Text style={styles.heroTitle}>교내 편의점 상품 요청 앱</Text>
        <Text style={styles.heroDesc}>
          필요한 상품을 확인하고 원하는 수량을 요청해보세요.
        </Text>
        <Pressable style={styles.primaryBtn} onPress={() => navigation.navigate('Login')}>
          <Text style={styles.primaryBtnText}>시작하기</Text>
        </Pressable>
      </View>
    </SafeAreaView>
  );
}

function LoginScreen({navigation}: any) {
  const [name, setName] = useState('');

  return (
    <SafeAreaView style={styles.page}>
      <Text style={styles.title}>간단 로그인</Text>
      <TextInput
        placeholder="이름 또는 학번 입력"
        value={name}
        onChangeText={setName}
        style={styles.input}
      />
      <Pressable
        style={styles.primaryBtn}
        onPress={() => {
          if (!name.trim()) {
            Alert.alert('입력 필요', '이름 또는 학번을 입력해 주세요.');
            return;
          }
          navigation.replace('ProductList');
        }}>
        <Text style={styles.primaryBtnText}>로그인</Text>
      </Pressable>
    </SafeAreaView>
  );
}

function ProductListScreen({navigation}: any) {
  const [keyword, setKeyword] = useState('');
  const [category, setCategory] = useState('전체');

  const categories = ['전체', ...new Set(PRODUCTS.map(p => p.category))];

  const filtered = useMemo(() => {
    return PRODUCTS.filter(p => {
      const categoryOk = category === '전체' || p.category === category;
      const keywordOk = p.name.includes(keyword) || p.description.includes(keyword);
      return categoryOk && keywordOk;
    });
  }, [keyword, category]);

  return (
    <SafeAreaView style={styles.page}>
      <Text style={styles.title}>상품 목록</Text>
      <TextInput
        placeholder="상품명 검색"
        value={keyword}
        onChangeText={setKeyword}
        style={styles.input}
      />

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

      <FlatList
        data={filtered}
        keyExtractor={item => item.id}
        renderItem={({item}) => (
          <Pressable
            style={styles.card}
            onPress={() => navigation.navigate('ProductDetail', {product: item})}>
            <Text style={styles.cardTitle}>{item.name}</Text>
            <Text style={styles.cardMeta}>{item.category}</Text>
            <Text style={styles.cardMeta}>재고: {item.stock > 0 ? `${item.stock}개` : '품절'}</Text>
          </Pressable>
        )}
        ListEmptyComponent={<Text style={styles.emptyText}>검색 결과가 없습니다.</Text>}
      />

      <Pressable style={styles.secondaryBtn} onPress={() => navigation.navigate('MyRequests')}>
        <Text style={styles.secondaryBtnText}>내 요청 목록 보기</Text>
      </Pressable>
    </SafeAreaView>
  );
}

function ProductDetailScreen({navigation, route}: any) {
  const {product} = route.params as {product: Product};

  return (
    <SafeAreaView style={styles.page}>
      <Text style={styles.title}>{product.name}</Text>
      <View style={styles.card}>
        <Text style={styles.cardMeta}>카테고리: {product.category}</Text>
        <Text style={styles.cardMeta}>설명: {product.description}</Text>
        <Text style={styles.cardMeta}>재고: {product.stock}개</Text>
      </View>
      <Pressable
        style={styles.primaryBtn}
        onPress={() => navigation.navigate('RequestQty', {product})}
        disabled={product.stock <= 0}>
        <Text style={styles.primaryBtnText}>{product.stock > 0 ? '수량 요청하기' : '품절 상품'}</Text>
      </Pressable>
    </SafeAreaView>
  );
}

function RequestQtyScreen({navigation, route, addRequest}: any) {
  const {product} = route.params as {product: Product};
  const [qty, setQty] = useState('1');

  return (
    <SafeAreaView style={styles.page}>
      <Text style={styles.title}>요청 수량 입력</Text>
      <Text style={styles.cardMeta}>{product.name}</Text>
      <TextInput
        keyboardType="number-pad"
        value={qty}
        onChangeText={setQty}
        style={styles.input}
      />

      <Pressable
        style={styles.primaryBtn}
        onPress={() => {
          const num = Number(qty);
          if (!Number.isInteger(num) || num <= 0) {
            Alert.alert('입력 오류', '1개 이상 정수로 입력해 주세요.');
            return;
          }

          const item: RequestItem = {
            id: `r-${Date.now()}`,
            productId: product.id,
            productName: product.name,
            qty: num,
            createdAt: new Date().toLocaleString('ko-KR'),
          };

          addRequest(item);
          navigation.navigate('RequestDone', {item});
        }}>
        <Text style={styles.primaryBtnText}>요청 제출</Text>
      </Pressable>
    </SafeAreaView>
  );
}

function RequestDoneScreen({navigation, route}: any) {
  const {item} = route.params as {item: RequestItem};

  return (
    <SafeAreaView style={styles.page}>
      <Text style={styles.title}>요청 완료</Text>
      <View style={styles.card}>
        <Text style={styles.cardMeta}>상품: {item.productName}</Text>
        <Text style={styles.cardMeta}>요청 수량: {item.qty}</Text>
        <Text style={styles.cardMeta}>요청 시각: {item.createdAt}</Text>
      </View>
      <Pressable
        style={styles.secondaryBtn}
        onPress={() => navigation.navigate('MyRequests')}>
        <Text style={styles.secondaryBtnText}>내 요청 목록 확인</Text>
      </Pressable>
      <Pressable
        style={styles.primaryBtn}
        onPress={() => navigation.navigate('ProductList')}>
        <Text style={styles.primaryBtnText}>상품 목록으로</Text>
      </Pressable>
    </SafeAreaView>
  );
}

function MyRequestsScreen({requests}: {requests: RequestItem[]}) {
  return (
    <SafeAreaView style={styles.page}>
      <Text style={styles.title}>내 요청 목록</Text>
      <FlatList
        data={requests}
        keyExtractor={item => item.id}
        renderItem={({item}) => (
          <View style={styles.card}>
            <Text style={styles.cardTitle}>{item.productName}</Text>
            <Text style={styles.cardMeta}>수량: {item.qty}</Text>
            <Text style={styles.cardMeta}>{item.createdAt}</Text>
          </View>
        )}
        ListEmptyComponent={<Text style={styles.emptyText}>아직 요청 내역이 없습니다.</Text>}
      />
    </SafeAreaView>
  );
}

export default function App() {
  const [requests, setRequests] = useState<RequestItem[]>([]);

  useEffect(() => {
    const loadRequests = async () => {
      try {
        const stored = await AsyncStorage.getItem(REQUESTS_STORAGE_KEY);
        if (!stored) {
          return;
        }

        const parsed = JSON.parse(stored) as RequestItem[];
        if (Array.isArray(parsed)) {
          setRequests(parsed);
        }
      } catch {
        // 저장소 읽기 실패 시 빈 목록 유지
      }
    };

    loadRequests();
  }, []);

  useEffect(() => {
    const saveRequests = async () => {
      try {
        await AsyncStorage.setItem(REQUESTS_STORAGE_KEY, JSON.stringify(requests));
      } catch {
        // 저장 실패 시에도 화면 흐름 유지
      }
    };

    saveRequests();
  }, [requests]);

  const addRequest = (item: RequestItem) => {
    setRequests(prev => [item, ...prev]);
  };

  return (
    <NavigationContainer>
      <Stack.Navigator screenOptions={{headerShown: true}}>
        <Stack.Screen name="Start" component={StartScreen} options={{title: '시작'}} />
        <Stack.Screen name="Login" component={LoginScreen} options={{title: '로그인'}} />
        <Stack.Screen name="ProductList" component={ProductListScreen} options={{title: '상품 목록'}} />
        <Stack.Screen name="ProductDetail" component={ProductDetailScreen} options={{title: '상품 상세'}} />
        <Stack.Screen name="RequestQty" options={{title: '수량 요청'}}>
          {props => <RequestQtyScreen {...props} addRequest={addRequest} />}
        </Stack.Screen>
        <Stack.Screen name="RequestDone" component={RequestDoneScreen} options={{title: '요청 완료'}} />
        <Stack.Screen name="MyRequests" options={{title: '내 요청'}}>
          {props => <MyRequestsScreen {...props} requests={requests} />}
        </Stack.Screen>
      </Stack.Navigator>
    </NavigationContainer>
  );
}

const styles = StyleSheet.create({
  page: {
    flex: 1,
    backgroundColor: '#F4F7FB',
    padding: 16,
  },
  heroCard: {
    marginTop: 36,
    borderRadius: 24,
    backgroundColor: '#0B3D91',
    padding: 24,
  },
  badge: {
    color: '#FFE9A8',
    fontWeight: '700',
    marginBottom: 8,
  },
  heroTitle: {
    fontSize: 28,
    color: '#FFF',
    fontWeight: '800',
  },
  heroDesc: {
    marginTop: 8,
    color: '#D7E6FF',
    marginBottom: 20,
  },
  title: {
    fontSize: 22,
    fontWeight: '800',
    marginBottom: 12,
    color: '#1F2937',
  },
  input: {
    borderWidth: 1,
    borderColor: '#D1D5DB',
    borderRadius: 12,
    backgroundColor: '#FFF',
    paddingHorizontal: 12,
    paddingVertical: 10,
    marginBottom: 10,
  },
  rowWrap: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 8,
    marginBottom: 10,
  },
  chip: {
    borderRadius: 999,
    borderWidth: 1,
    borderColor: '#CBD5E1',
    paddingHorizontal: 12,
    paddingVertical: 7,
    backgroundColor: '#FFF',
  },
  chipActive: {
    backgroundColor: '#0B3D91',
    borderColor: '#0B3D91',
  },
  chipText: {color: '#334155'},
  chipTextActive: {color: '#FFF'},
  card: {
    backgroundColor: '#FFF',
    borderRadius: 14,
    padding: 14,
    marginBottom: 10,
    borderWidth: 1,
    borderColor: '#E5E7EB',
  },
  cardTitle: {
    fontSize: 16,
    fontWeight: '700',
    color: '#111827',
    marginBottom: 4,
  },
  cardMeta: {
    color: '#4B5563',
    marginBottom: 2,
  },
  primaryBtn: {
    backgroundColor: '#0B3D91',
    paddingVertical: 12,
    borderRadius: 12,
    alignItems: 'center',
    marginTop: 10,
  },
  primaryBtnText: {
    color: '#FFF',
    fontWeight: '700',
  },
  secondaryBtn: {
    borderWidth: 1,
    borderColor: '#0B3D91',
    backgroundColor: '#EAF1FF',
    paddingVertical: 12,
    borderRadius: 12,
    alignItems: 'center',
    marginVertical: 10,
  },
  secondaryBtnText: {
    color: '#0B3D91',
    fontWeight: '700',
  },
  emptyText: {
    textAlign: 'center',
    marginTop: 20,
    color: '#6B7280',
  },
});
