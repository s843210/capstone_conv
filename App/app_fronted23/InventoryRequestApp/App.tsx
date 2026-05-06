import React, {useEffect, useState} from 'react';
import {SafeAreaView, Text} from 'react-native';
import {NavigationContainer} from '@react-navigation/native';
import {createNativeStackNavigator} from '@react-navigation/native-stack';
import AsyncStorage from '@react-native-async-storage/async-storage';
import {RequestItem, RootStackParamList} from './src/types';
import StartScreen from './src/screens/StartScreen';
import LoginScreen from './src/screens/LoginScreen';
import ProductListScreen from './src/screens/ProductListScreen';
import ProductDetailScreen from './src/screens/ProductDetailScreen';
import RequestQtyScreen from './src/screens/RequestQtyScreen';
import RequestDoneScreen from './src/screens/RequestDoneScreen';
import MyRequestsScreen from './src/screens/MyRequestsScreen';
import {styles} from './src/styles/commonStyles';
import {STORAGE_KEYS} from './src/data/appConstants';

const Stack = createNativeStackNavigator<RootStackParamList>();

export default function App() {
  const [requests, setRequests] = useState<RequestItem[]>([]);
  const [currentUser, setCurrentUser] = useState('');
  const [isInitializing, setIsInitializing] = useState(true);

  useEffect(() => {
    const initializeApp = async () => {
      let nextRequests: RequestItem[] = [];
      let nextUser = '';

      try {
        const [storedRequests, storedUser] = await Promise.all([
          AsyncStorage.getItem(STORAGE_KEYS.requests),
          AsyncStorage.getItem(STORAGE_KEYS.user),
        ]);

        if (storedRequests) {
          try {
            const parsed = JSON.parse(storedRequests) as RequestItem[];
            if (Array.isArray(parsed)) {
              nextRequests = parsed;
            }
          } catch {
            nextRequests = [];
          }
        }

        if (storedUser && storedUser.trim()) {
          nextUser = storedUser.trim();
        }
      } catch {
        nextRequests = [];
        nextUser = '';
      } finally {
        setRequests(nextRequests);
        setCurrentUser(nextUser);
        setIsInitializing(false);
      }
    };

    initializeApp();
  }, []);

  const addRequest = async (item: RequestItem): Promise<boolean> => {
    try {
      const nextRequests = [item, ...requests];
      await AsyncStorage.setItem(STORAGE_KEYS.requests, JSON.stringify(nextRequests));
      setRequests(nextRequests);
      return true;
    } catch {
      return false;
    }
  };

  const removeRequest = async (requestId: string): Promise<boolean> => {
    try {
      const nextRequests = requests.filter(request => request.id !== requestId);
      await AsyncStorage.setItem(STORAGE_KEYS.requests, JSON.stringify(nextRequests));
      setRequests(nextRequests);
      return true;
    } catch {
      return false;
    }
  };

  const updateRequestQty = async (requestId: string, qty: number): Promise<boolean> => {
    try {
      const nextRequests = requests.map(request =>
        request.id === requestId ? {...request, qty} : request,
      );
      await AsyncStorage.setItem(STORAGE_KEYS.requests, JSON.stringify(nextRequests));
      setRequests(nextRequests);
      return true;
    } catch {
      return false;
    }
  };

  const loginUser = async (name: string): Promise<boolean> => {
    try {
      await AsyncStorage.setItem(STORAGE_KEYS.user, name);
      setCurrentUser(name);
      return true;
    } catch {
      return false;
    }
  };

  const logoutUser = async (): Promise<boolean> => {
    try {
      await AsyncStorage.removeItem(STORAGE_KEYS.user);
      setCurrentUser('');
      return true;
    } catch {
      return false;
    }
  };

  if (isInitializing) {
    return (
      <SafeAreaView style={styles.page}>
        <Text style={styles.emptyText}>앱 정보를 불러오는 중입니다...</Text>
      </SafeAreaView>
    );
  }

  return (
    <NavigationContainer>
      <Stack.Navigator initialRouteName={currentUser ? 'ProductList' : 'Start'} screenOptions={{headerShown: true}}>
        <Stack.Screen name="Start" component={StartScreen} options={{title: '시작'}} />
        <Stack.Screen name="Login" options={{title: '로그인'}}>
          {props => <LoginScreen {...props} loginUser={loginUser} />}
        </Stack.Screen>
        <Stack.Screen name="ProductList" options={{title: '상품 목록'}}>
          {props => <ProductListScreen {...props} currentUser={currentUser} logoutUser={logoutUser} />}
        </Stack.Screen>
        <Stack.Screen name="ProductDetail" component={ProductDetailScreen} options={{title: '상품 상세'}} />
        <Stack.Screen name="RequestQty" options={{title: '수량 요청'}}>
          {props => <RequestQtyScreen {...props} addRequest={addRequest} currentUser={currentUser} />}
        </Stack.Screen>
        <Stack.Screen name="RequestDone" component={RequestDoneScreen} options={{title: '요청 완료'}} />
        <Stack.Screen name="MyRequests" options={{title: '내 요청'}}>
          {props => (
            <MyRequestsScreen
              {...props}
              requests={requests}
              removeRequest={removeRequest}
              updateRequestQty={updateRequestQty}
              currentUser={currentUser}
              logoutUser={logoutUser}
            />
          )}
        </Stack.Screen>
      </Stack.Navigator>
    </NavigationContainer>
  );
}

