import React, {useEffect, useRef, useState} from 'react';
import {NavigationContainer} from '@react-navigation/native';
import {createNativeStackNavigator} from '@react-navigation/native-stack';
import AsyncStorage from '@react-native-async-storage/async-storage';
import * as SplashScreen from 'expo-splash-screen';
import {RequestItem, RootStackParamList, Suggestion} from './src/types';
import LoginScreen from './src/screens/LoginScreen';
import ProductListScreen from './src/screens/ProductListScreen';
import ProductDetailScreen from './src/screens/ProductDetailScreen';
import RequestQtyScreen from './src/screens/RequestQtyScreen';
import RequestDoneScreen from './src/screens/RequestDoneScreen';
import MyRequestsScreen from './src/screens/MyRequestsScreen';
import SuggestionsScreen from './src/screens/SuggestionsScreen';
import SuggestionWriteScreen from './src/screens/SuggestionWriteScreen';
import SuggestionDetailScreen from './src/screens/SuggestionDetailScreen';
import SuggestionEditScreen from './src/screens/SuggestionEditScreen';
import {STORAGE_KEYS} from './src/data/appConstants';
import {loadSuggestions, saveSuggestions} from './src/data/suggestionStorage';
import {deleteStudentRequest, fetchStudentRequests, submitStudentRequest} from './src/api/studentApi';

const Stack = createNativeStackNavigator<RootStackParamList>();
const SPLASH_TEST_DELAY_MS = 2000;

SplashScreen.preventAutoHideAsync().catch(() => undefined);

export default function App() {
  const [requests, setRequests] = useState<RequestItem[]>([]);
  const [suggestions, setSuggestions] = useState<Suggestion[]>([]);
  const suggestionsRef = useRef<Suggestion[]>([]);
  const [currentUser, setCurrentUser] = useState('');
  const [isInitializing, setIsInitializing] = useState(true);

  useEffect(() => {
    const initializeApp = async () => {
      let nextRequests: RequestItem[] = [];
      let nextUser = '';

      try {
        const [storedRequests, storedUser, storedSuggestions] = await Promise.all([
          AsyncStorage.getItem(STORAGE_KEYS.requests),
          AsyncStorage.getItem(STORAGE_KEYS.user),
          loadSuggestions(),
          new Promise(resolve => setTimeout(resolve, SPLASH_TEST_DELAY_MS)),
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

        setSuggestions(storedSuggestions);
      } catch {
        nextRequests = [];
        nextUser = '';
      } finally {
        setRequests(nextRequests);
        setCurrentUser(nextUser);
        setIsInitializing(false);
        SplashScreen.hideAsync().catch(() => undefined);
      }
    };

    initializeApp();
  }, []);

  useEffect(() => {
    suggestionsRef.current = suggestions;
  }, [suggestions]);

  useEffect(() => {
    if (isInitializing || !currentUser) {
      return;
    }

    let cancelled = false;

    const syncRequests = async () => {
      try {
        const serverRequests = await fetchStudentRequests(currentUser);
        if (cancelled) {
          return;
        }

        const nextRequests = serverRequests.map(request => ({
          id: `${request.salesDate}-${request.pluCode}`,
          pluCode: request.pluCode,
          productName: request.productName,
          qty: request.quantity,
          createdAt: new Date(request.requestedAt).toLocaleString('ko-KR'),
          salesDate: request.salesDate,
        }));

        await AsyncStorage.setItem(STORAGE_KEYS.requests, JSON.stringify(nextRequests));
        if (!cancelled) {
          setRequests(nextRequests);
        }
      } catch {
        // 서버 동기화 실패 시에는 마지막 로컬 요청 목록을 유지
      }
    };

    syncRequests();

    return () => {
      cancelled = true;
    };
  }, [currentUser, isInitializing]);

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
      const targetRequest = requests.find(request => request.id === requestId);
      if (!targetRequest) {
        return true;
      }

      await deleteStudentRequest({
        studentId: currentUser,
        salesDate: targetRequest.salesDate,
        pluCode: targetRequest.pluCode,
      });

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
      const targetRequest = requests.find(request => request.id === requestId);
      if (!targetRequest) {
        return false;
      }

      const response = await submitStudentRequest({
        studentId: currentUser,
        salesDate: targetRequest.salesDate,
        items: [
          {
            pluCode: targetRequest.pluCode,
            quantity: qty,
          },
        ],
      });

      const nextRequests = requests.map(request =>
        request.id === requestId ? {...request, qty, salesDate: response.salesDate} : request,
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

  const addSuggestion = async (suggestion: Suggestion): Promise<boolean> => {
    try {
      const nextSuggestions = [suggestion, ...suggestionsRef.current];
      await saveSuggestions(nextSuggestions);
      setSuggestions(nextSuggestions);
      return true;
    } catch {
      return false;
    }
  };

  const updateSuggestion = async (
    nextSuggestion: Suggestion,
    requestUser: string,
  ): Promise<boolean> => {
    try {
      const normalizedUser = requestUser.trim();
      const currentSuggestions = suggestionsRef.current;
      const targetSuggestion = currentSuggestions.find(item => item.id === nextSuggestion.id);
      if (!targetSuggestion || targetSuggestion.writer.trim() !== normalizedUser) {
        return false;
      }

      const nextSuggestions = currentSuggestions.map(item =>
        item.id === nextSuggestion.id ? {...nextSuggestion, writer: targetSuggestion.writer} : item,
      );
      await saveSuggestions(nextSuggestions);
      setSuggestions(nextSuggestions);
      return true;
    } catch {
      return false;
    }
  };

  const removeSuggestion = async (suggestionId: string, requestUser: string): Promise<boolean> => {
    try {
      const normalizedUser = requestUser.trim();
      const currentSuggestions = suggestionsRef.current;
      const targetSuggestion = currentSuggestions.find(item => item.id === suggestionId);
      if (!targetSuggestion || targetSuggestion.writer.trim() !== normalizedUser) {
        return false;
      }

      const nextSuggestions = currentSuggestions.filter(item => item.id !== suggestionId);
      await saveSuggestions(nextSuggestions);
      setSuggestions(nextSuggestions);
      return true;
    } catch {
      return false;
    }
  };

  const removeSuggestionsBulk = async (
    suggestionIds: string[],
    requestUser: string,
  ): Promise<{removedCount: number; failedCount: number}> => {
    try {
      let removedCount = 0;
      let failedCount = 0;

      const currentSuggestions = [...suggestionsRef.current];
      const selectableIds = new Set(currentSuggestions.map(item => item.id));
      const targetIds = suggestionIds.filter(id => selectableIds.has(id));

      if (targetIds.length === 0) {
        return {removedCount: 0, failedCount: suggestionIds.length};
      }

      const targetIdSet = new Set(targetIds);
      const nextSuggestions = currentSuggestions.filter(item => !targetIdSet.has(item.id));
      removedCount = targetIds.length;
      failedCount = suggestionIds.length - removedCount;

      await saveSuggestions(nextSuggestions);
      setSuggestions(nextSuggestions);
      return {removedCount, failedCount};
    } catch {
      return {removedCount: 0, failedCount: suggestionIds.length};
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
    return null;
  }

  return (
    <NavigationContainer>
      <Stack.Navigator
        initialRouteName={currentUser ? 'ProductList' : 'Login'}
        screenOptions={{headerShown: true}}>
        <Stack.Screen name="Login" options={{headerShown: false}}>
          {props => <LoginScreen {...props} loginUser={loginUser} />}
        </Stack.Screen>
        <Stack.Screen name="ProductList" options={{headerShown: false, title: '상품 목록'}}>
          {props => <ProductListScreen {...props} currentUser={currentUser} logoutUser={logoutUser} />}
        </Stack.Screen>
        <Stack.Screen name="ProductDetail" component={ProductDetailScreen} options={{title: '상품 상세'}} />
        <Stack.Screen name="RequestQty" options={{title: '수량 요청'}}>
          {props => <RequestQtyScreen {...props} addRequest={addRequest} currentUser={currentUser} />}
        </Stack.Screen>
        <Stack.Screen name="RequestDone" component={RequestDoneScreen} options={{title: '요청 완료'}} />
        <Stack.Screen name="MyRequests" options={{title: '내 요청 목록', headerBackTitle: '상품 목록'}}>
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
        <Stack.Screen name="Suggestions" options={{title: '건의사항', headerBackTitle: '상품 목록'}}>
          {props => (
            <SuggestionsScreen
              {...props}
              suggestions={suggestions}
              currentUser={currentUser}
              removeSuggestion={removeSuggestion}
              removeSuggestionsBulk={removeSuggestionsBulk}
            />
          )}
        </Stack.Screen>
        <Stack.Screen name="SuggestionWrite" options={{title: '건의사항 작성'}}>
          {props => (
            <SuggestionWriteScreen
              {...props}
              currentUser={currentUser}
              addSuggestion={addSuggestion}
            />
          )}
        </Stack.Screen>
        <Stack.Screen name="SuggestionEdit" options={{title: '건의사항'}}>
          {props => (
            <SuggestionEditScreen
              {...props}
              currentUser={currentUser}
              updateSuggestion={updateSuggestion}
            />
          )}
        </Stack.Screen>
        <Stack.Screen name="SuggestionDetail" options={{title: '건의사항'}}>
          {props => (
            <SuggestionDetailScreen
              {...props}
              currentUser={currentUser}
              removeSuggestion={removeSuggestion}
            />
          )}
        </Stack.Screen>
      </Stack.Navigator>
    </NavigationContainer>
  );
}











